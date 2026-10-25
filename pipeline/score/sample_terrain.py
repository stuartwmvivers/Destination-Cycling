#!/usr/bin/env python3
"""Sample terrain heights along every road edge of the network (build_network.py).

Each edge's road shape is densified so points are at most STEP metres apart, then heights are read by
bilinear interpolation from the Copernicus GLO-30 tiles after a 5x5 median filter (~150 m). GLO-30 is a
surface model (tree tops and roofs, not bare ground); the filter removes isolated spikes, but forest
canopy along a road can still bias heights. Then, per edge:
  - bridges and tunnels (OSM tags): the terrain is the valley below or the mountain above, so heights are
    drawn straight between the edge's two ends;
  - a median of 3 neighbouring points, applied twice, removes one- or two-point blips. Edge end points are
    left as they are, so edges meeting at a junction agree on its height.

Output (cache WORK/profiles.npz): prof_off (per edge, into the arrays below), prof_d (metres from the
edge's start, u end), prof_z (metres above sea level). Points over sea or outside any tile get 0.
Usage (score venv): python pipeline/score/sample_terrain.py
"""
import glob, os, time
import numpy as np, rasterio
from scipy import ndimage
from common import DEM, WORK, dem_name

STEP = 30.0   # metres between profile points (at most)

def haversine(la1, lo1, la2, lo2):
    p1, p2 = np.radians(la1), np.radians(la2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lo2 - lo1) / 2) ** 2
    return 2 * 6371008.8 * np.arcsin(np.sqrt(a))

def densify(goff, glat, glon):
    """Insert points so consecutive points within an edge are <= STEP apart. Returns (off, lat, lon, d)."""
    glat, glon = glat.astype(np.float64), glon.astype(np.float64)
    seg = haversine(glat[:-1], glon[:-1], glat[1:], glon[1:])
    last = np.zeros(len(glat), bool); last[goff[1:] - 1] = True        # last point of each edge: no segment after it
    seg[last[:-1]] = 0
    n_ins = np.where(last[:-1], 0, np.ceil(seg / STEP).astype(np.int64))  # pieces per segment (>= 1 within an edge)
    n_ins = np.maximum(n_ins, np.where(last[:-1], 0, 1))
    # every original point, then the interpolated points of the segment that starts at it
    reps = np.r_[n_ins, 1]; reps[last] = 1
    start = np.repeat(np.arange(len(glat)), reps)
    frac = np.arange(len(start)) - np.repeat(np.cumsum(reps) - reps, reps)
    frac = frac / np.repeat(np.where(reps > 0, reps, 1), reps)
    nxt = np.minimum(start + 1, len(glat) - 1)
    is_last = last[start]
    lat = np.where(is_last, glat[start], glat[start] + frac * (glat[nxt] - glat[start]))
    lon = np.where(is_last, glon[start], glon[start] + frac * (glon[nxt] - glon[start]))
    edge_of_pt = np.repeat(np.arange(len(goff) - 1), np.diff(goff))
    edge = edge_of_pt[start]
    off = np.r_[0, np.cumsum(np.bincount(edge, minlength=len(goff) - 1))]
    step = np.r_[0, haversine(lat[:-1], lon[:-1], lat[1:], lon[1:])]
    step[off[:-1]] = 0
    d = np.cumsum(step); d -= np.repeat(d[off[:-1]], np.diff(off))
    return off, lat, lon, d

def sample(lat, lon):
    z = np.zeros(len(lat), np.float32)
    tlat, tlon = np.floor(lat).astype(int), np.floor(lon).astype(int)
    key = tlat * 1000 + tlon
    order = np.argsort(key, kind='stable'); ks = key[order]
    bounds = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1], True])
    for a, b in zip(bounds[:-1], bounds[1:]):
        idx = order[a:b]; la0, lo0 = tlat[idx[0]], tlon[idx[0]]
        f = os.path.join(DEM, dem_name(la0, lo0) + '.tif')
        if not os.path.exists(f): continue
        with rasterio.open(f) as r:
            g = ndimage.median_filter(r.read(1), size=5)
            ncol = r.width; nrow = r.height
        # pixel centres sit on whole arc-seconds: col = (lon - lo0) * ncol, row = (la0 + 1 - lat) * nrow
        c = np.clip((lon[idx] - lo0) * ncol, 0, ncol - 1.000001); rw = np.clip((la0 + 1 - lat[idx]) * nrow, 0, nrow - 1.000001)
        c0, r0 = c.astype(int), rw.astype(int); fc, fr = c - c0, rw - r0
        z[idx] = (g[r0, c0] * (1 - fc) * (1 - fr) + g[r0, c0 + 1] * fc * (1 - fr)
                  + g[r0 + 1, c0] * (1 - fc) * fr + g[r0 + 1, c0 + 1] * fc * fr)
    return z

def fix_structures(off, d, z, struct):
    """Straight line between the two ends of every bridge or tunnel edge."""
    z = z.copy()
    for e in np.flatnonzero(struct > 0):
        a, b = off[e], off[e + 1]
        if b - a > 2 and d[b - 1] > 0:
            z[a + 1:b - 1] = z[a] + (z[b - 1] - z[a]) * (d[a + 1:b - 1] / d[b - 1])
    print(f'bridges/tunnels levelled: {int((struct == 1).sum()):,} bridge and {int((struct == 2).sum()):,} tunnel edges', flush=True)
    return z

def smooth(off, z, passes=2):
    """Median of each interior point and its two neighbours within the same edge; edge ends unchanged."""
    interior = np.ones(len(z), bool); interior[off[:-1]] = False; interior[off[1:] - 1] = False
    idx = np.flatnonzero(interior)
    for _ in range(passes):
        z = z.copy()
        z[idx] = np.median(np.stack([z[idx - 1], z[idx], z[idx + 1]]), axis=0)
    return z

def main():
    t = time.time()
    n = np.load(os.path.join(WORK, 'network.npz'))
    off, lat, lon, d = densify(n['geom_off'], n['geom_lat'], n['geom_lon'])
    print(f'{len(off) - 1:,} edges, {len(lat):,} profile points ({time.time() - t:.0f} s)', flush=True)
    z = sample(lat, lon)
    print(f'sampled heights ({time.time() - t:.0f} s); range {z.min():.0f}..{z.max():.0f} m', flush=True)
    z = fix_structures(off, d, z, n['edge_struct'])
    z = smooth(off, z)
    out = os.path.join(WORK, 'profiles.npz')
    np.savez(out, prof_off=off, prof_d=d.astype(np.float32), prof_z=z)
    print(f'-> {out} ({os.path.getsize(out) / 1e6:.0f} MB, {time.time() - t:.0f} s)')

if __name__ == '__main__':
    main()
