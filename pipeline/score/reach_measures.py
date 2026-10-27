#!/usr/bin/env python3
"""Raw 'within reach' measures for the score (spec section 3), on 1 km grids, from the cycling network
(network.npz + profiles.npz), off-road features (features.npz) and ESA WorldCover land cover.

Each measure sums features within a straight-line radius of a point (a disc, by FFT convolution): far faster
than road distances for all of Spain, and close enough for these secondary measures.
  quiet_km    minor paved roads: tertiary(+link) and unclassified 1.0, secondary(+link) and 'road' 0.5;
              primary roads and town streets (residential) don't count; roads in built-up land (WorldCover) count
              URBAN_QUIET (0.1; 0.3 until 25 Oct 2026, when Barcelona's suburbs still ranked high), so suburban sprawl
              doesn't look like quiet countryside. Radius 20 km (~26 km by road).
  loops       junctions where >= 3 minor roads meet (a proxy for loop-ability); URBAN_QUIET in built-up land. Radius 20 km.
  flat_km     minor roads (as quiet_km) averaging under 2% gradient: recovery-day riding. Radius 20 km.
  gravel_km   gravel tracks (features cat 1) x countryside quality from land cover (forest, scrub, grass,
              wetland 1.0; farmland 0.6 (pleasant but not "nice countryside" in the way woods and hills are); bare 0.6; snow 0.5; built-up 0.2; water 0). Radius 15 km.
  walk_km     paths 1.0 (0.3 in built-up land), mountain paths 2.0, rough tracks 0.5, plus their length again if
              part of a waymarked hiking route. Radius 15 km.
  peaks       named peaks >= 300 m, weighted by height / 1000. Radius 15 km.
  land15/20   km2 of usable land within 15 / 20 km: land in WorldCover (not water, not sea or no-data) AND within
              LAND_NEAR_KM of a junction of the Spanish network, so Portugal, France and Andorra (outside the OSM
              extract, so roadless here) don't count as empty land. score_export.py divides by it (25 Oct 2026).
  built5/land5  km2 of built-up land (WorldCover class 50) and of usable land within 5 km: how built-up the base's
              own surroundings are, for the page's built-up penalty (owner, 25 Oct 2026).
Output: WORK/reach.npz (one grid per area: mainland + Balearics, Canaries).
Usage (score venv): python pipeline/score/reach_measures.py [--check]
"""
import glob, os, sys, time
import numpy as np, rasterio
from rasterio.enums import Resampling
from scipy.signal import fftconvolve
from common import WORK, LANDCOVER

AREAS = {'mainland': (35.8, 44.0, -9.6, 4.6), 'canaries': (27.5, 29.5, -18.3, -13.3)}
RADIUS = {'quiet_km': 20, 'loops': 20, 'flat_km': 20, 'gravel_km': 15, 'walk_km': 15, 'peaks': 15}
URBAN_QUIET = 0.1      # quiet roads and junctions in built-up land
LAND_NEAR_KM = 3
ROAD_W = {'tertiary': 1.0, 'tertiary_link': 1.0, 'unclassified': 1.0, 'secondary': 0.5, 'secondary_link': 0.5, 'road': 0.5}
LC_QUALITY = {10: 1.0, 20: 1.0, 30: 1.0, 40: 0.6, 50: 0.2, 60: 0.6, 70: 0.5, 80: 0.0, 90: 1.0, 95: 1.0, 100: 1.0}

def landcover_sampler():
    """Land-cover class at points, from the 10 m tiles read at ~100 m (their built-in overviews)."""
    tiles = {}
    for f in glob.glob(os.path.join(LANDCOVER, '*.tif')):
        name = os.path.basename(f)[:-4]                         # e.g. N39W003
        la0 = int(name[1:3]); lo0 = int(name[4:7]) * (1 if name[3] == 'E' else -1)
        with rasterio.open(f) as r:
            tiles[(la0, lo0)] = r.read(1, out_shape=(3600, 3600), resampling=Resampling.nearest)
    def sample(lat, lon):
        out = np.zeros(len(lat), np.uint8)
        la0 = (np.floor(lat / 3) * 3).astype(int); lo0 = (np.floor(lon / 3) * 3).astype(int)
        for (a, b), g in tiles.items():
            m = (la0 == a) & (lo0 == b)
            if not m.any(): continue
            row = np.clip(((a + 3 - lat[m]) / 3 * 3600).astype(int), 0, 3599); col = np.clip(((lon[m] - b) / 3 * 3600).astype(int), 0, 3599)
            out[m] = g[row, col]
        return out
    return sample

class Grid:
    def __init__(self, s, n, w, e):
        self.s, self.n, self.w, self.e = s, n, w, e
        self.coslat = np.cos(np.radians((s + n) / 2))
        self.dy = 1 / 111.2; self.dx = 1 / (111.2 * self.coslat)   # 1 km cells
        self.ny = int((n - s) / self.dy) + 1; self.nx = int((e - w) / self.dx) + 1
    def cells(self, lat, lon):
        r = ((self.n - lat) / self.dy).astype(int); c = ((lon - self.w) / self.dx).astype(int)
        ok = (r >= 0) & (r < self.ny) & (c >= 0) & (c < self.nx)
        return r, c, ok
    def add(self, lat, lon, weight):
        g = np.zeros((self.ny, self.nx), np.float32)
        r, c, ok = self.cells(lat, lon)
        np.add.at(g, (r[ok], c[ok]), weight[ok])
        return g
    def disc_sum(self, g, km):
        k = int(km); y, x = np.mgrid[-k:k + 1, -k:k + 1]
        return np.maximum(fftconvolve(g, ((x * x + y * y) <= km * km).astype(np.float32), mode='same'), 0).astype(np.float32)

def road_layers(lc):
    n = np.load(os.path.join(WORK, 'network.npz')); p = np.load(os.path.join(WORK, 'profiles.npz'))
    cls = n['classes'][n['edge_cls']]
    w = np.array([ROAD_W.get(c, 0.0) for c in n['classes']], np.float32)[n['edge_cls']]
    # average gradient per edge: total up-and-down over length
    off, pz = p['prof_off'], p['prof_z'].astype(np.float64)
    dz = np.abs(np.diff(pz)); dz[off[1:-1] - 1] = 0          # no step across edge boundaries
    climb = np.add.reduceat(np.r_[dz, 0], off[:-1])
    grad = climb / np.maximum(n['edge_len'], 1)
    flat = grad < 0.02
    # spread each edge's length over its road shape (segment midpoints), so long edges land in the right cells
    goff, glat, glon = n['geom_off'], n['geom_lat'].astype(np.float64), n['geom_lon'].astype(np.float64)
    seg = np.hypot(np.diff(glat) * 111195.0, np.diff(glon) * 111195.0 * np.cos(np.radians(glat[:-1])))
    edge_of = np.repeat(np.arange(len(goff) - 1), np.diff(goff))
    valid = edge_of[:-1] == edge_of[1:]
    mlat, mlon, L, e = ((glat[:-1] + glat[1:]) / 2)[valid], ((glon[:-1] + glon[1:]) / 2)[valid], seg[valid] / 1000, edge_of[:-1][valid]
    # junctions where >= 3 minor roads meet
    minor = w > 0
    deg = np.bincount(np.r_[n['edge_u'][minor], n['edge_v'][minor]], minlength=len(n['node_lat']))
    j = deg >= 3
    urban = np.where(lc(mlat, mlon) == 50, 0.3, 1.0).astype(np.float32)
    uquiet = np.where(urban < 1, URBAN_QUIET, 1.0).astype(np.float32)
    jurban = np.where(lc(n['node_lat'][j], n['node_lon'][j]) == 50, URBAN_QUIET, 1.0).astype(np.float32)
    return dict(quiet=(mlat, mlon, L * w[e] * uquiet), flat=(mlat, mlon, L * (w[e] > 0) * flat[e] * urban),
                loops=(n['node_lat'][j], n['node_lon'][j], jurban), nodes=(n['node_lat'], n['node_lon']))

def land_grid(G, lc, nodes):
    """Fractions (0-1) of each 1 km cell that are usable land and built-up land: WorldCover (3 x 3 samples per cell),
    near the network."""
    rows, cols = np.mgrid[0:G.ny, 0:G.nx]
    frac = np.zeros((G.ny, G.nx), np.float32); built = np.zeros((G.ny, G.nx), np.float32)
    for dy in (-1 / 3, 0, 1 / 3):
        for dx in (-1 / 3, 0, 1 / 3):
            la = (G.n - (rows + 0.5 + dy) * G.dy).ravel(); lo = (G.w + (cols + 0.5 + dx) * G.dx).ravel()
            c = lc(la, lo).reshape(G.ny, G.nx)
            frac += ((c != 0) & (c != 80)) / 9; built += (c == 50) / 9
    has = G.add(nodes[0].astype(np.float64), nodes[1].astype(np.float64), np.ones(len(nodes[0]), np.float32)) > 0
    near = G.disc_sum(has.astype(np.float32), LAND_NEAR_KM) > 0.5
    return frac * near, built * near

def main(check):
    t = time.time()
    lc = landcover_sampler(); print(f'land cover loaded ({time.time() - t:.0f} s)', flush=True)
    R = road_layers(lc); print(f'road layers ({time.time() - t:.0f} s)', flush=True)
    f = np.load(os.path.join(WORK, 'features.npz'))
    flat_, flon, flen, fcat, frt = f['lat'].astype(np.float64), f['lon'].astype(np.float64), f['length'] / 1000, f['cat'], f['route']
    cls = lc(flat_, flon)
    quality = np.vectorize(lambda c: LC_QUALITY.get(int(c), 0.5))(np.arange(256))[cls].astype(np.float32)
    gravel = flen * (fcat == 1) * quality
    walk_w = np.select([fcat == 2, fcat == 3, fcat == 4], [np.where(cls == 50, 0.3, 1.0), 2.0, 0.5], 0.0).astype(np.float32)
    walk = flen * walk_w * (1 + frt)
    pk = f['peak_ele'] >= 300
    print(f'features weighted ({time.time() - t:.0f} s)', flush=True)
    out = {}
    for area, box in AREAS.items():
        G = Grid(*box)
        layers = {'quiet_km': G.add(*R['quiet']), 'flat_km': G.add(*R['flat']), 'loops': G.add(*R['loops']),
                  'gravel_km': G.add(flat_, flon, gravel), 'walk_km': G.add(flat_, flon, walk),
                  'peaks': G.add(f['peak_lat'][pk].astype(np.float64), f['peak_lon'][pk].astype(np.float64), f['peak_ele'][pk] / 1000)}
        for k, g in layers.items():
            out[f'{area}_{k}'] = G.disc_sum(g, RADIUS[k])
        land, built = land_grid(G, lc, R['nodes'])
        for km in (5, 15, 20): out[f'{area}_land{km}'] = G.disc_sum(land, km)
        out[f'{area}_built5'] = G.disc_sum(built, 5)
        out[f'{area}_box'] = np.array(box); out[f'{area}_shape'] = np.array([G.ny, G.nx])
        print(f'{area}: {G.ny} x {G.nx} grid ({time.time() - t:.0f} s)', flush=True)
    np.savez_compressed(os.path.join(WORK, 'reach.npz'), **out)
    if check: report(out)

def at(out, lat, lon):
    """All measures at a point."""
    for area, box in AREAS.items():
        s, n, w, e = box
        if s <= lat <= n and w <= lon <= e:
            G = Grid(*box); r, c, ok = G.cells(np.array([lat]), np.array([lon]))
            return {k: float(out[f'{area}_{k}'][r[0], c[0]]) for k in RADIUS}
    return None

def report(out):
    PLACES = [('Port de Pollença', 39.905, 3.087), ('Sóller', 39.767, 2.715), ('Girona', 41.980, 2.820), ('Olot', 42.180, 2.490),
              ('Calpe', 38.645, 0.044), ('Torrox Costa', 36.728, -3.955), ('Cómpeta', 36.834, -3.973), ('Ronda', 36.742, -5.166),
              ('Granada', 37.177, -3.599), ('Jaca', 42.570, -0.549), ('Puerto de la Cruz', 28.414, -16.548),
              ('Benidorm', 38.541, -0.131), ('Valencia', 39.470, -0.376), ('Tomelloso', 39.157, -3.025)]
    print(f"\n{'place':18} " + ' '.join(f'{k:>10}' for k in RADIUS))
    for name, la, lo in PLACES:
        m = at(out, la, lo)
        print(f'{name:18} ' + ' '.join(f'{m[k]:10.0f}' for k in RADIUS))

if __name__ == '__main__':
    main('--check' in sys.argv)
