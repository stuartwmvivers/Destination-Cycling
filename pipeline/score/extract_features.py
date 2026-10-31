#!/usr/bin/env python3
"""Extract the off-road features the reach measures need from the OSM extracts in the cache.

Categories (one per way):
  1 gravel         highway=track grade1-3 (or untagged grade with a good unpaved surface), and unpaved
                   cycleways/paths open to bikes. The gravel-riding network.
  2 path           highway=path/footway/bridleway outside obvious urban use (no sidewalks, crossings, steps).
  3 mountain path  a path with sac_scale mountain_hiking or harder (proper hill walking).
  4 rough track    highway=track grade4-5: walkable, not much fun to ride.
Each way is stored as segment midpoints with segment lengths, plus whether it is part of a waymarked hiking route
(route=hiking/foot relations). Peaks: natural=peak nodes with a height.
Output: WORK/features.npz.  Usage (score venv): python pipeline/score/extract_features.py
"""
import glob, os, re, time
from array import array
import numpy as np
import osmium
from common import OSM, WORK

GOOD_UNPAVED = {'gravel', 'fine_gravel', 'compacted', 'dirt', 'earth', 'ground', 'unpaved'}
BAD_SURFACE = {'mud', 'sand', 'grass', 'rock', 'stone', 'pebblestone', 'scree'}
NO = {'no', 'private', 'military'}
MOUNTAIN = {'mountain_hiking', 'demanding_mountain_hiking', 'alpine_hiking', 'demanding_alpine_hiking', 'difficult_alpine_hiking'}

def category(t):
    h = t.get('highway')
    if t.get('access') in NO and t.get('bicycle') not in ('yes', 'designated', 'permissive') and t.get('foot') not in ('yes', 'designated', 'permissive'):
        return 0
    surf = t.get('surface')
    if h == 'track':
        g = t.get('tracktype')
        if g in ('grade1', 'grade2', 'grade3') and surf not in BAD_SURFACE: return 1
        if g is None and surf in GOOD_UNPAVED: return 1
        if g in ('grade4', 'grade5') or surf in BAD_SURFACE: return 4
        return 1 if g is None else 4
    if h in ('cycleway', 'path') and surf in GOOD_UNPAVED and t.get('bicycle') in ('yes', 'designated', 'permissive'):
        return 1
    if h in ('path', 'footway', 'bridleway'):
        if t.get('footway') in ('sidewalk', 'crossing', 'access_aisle') or t.get('indoor') == 'yes' or t.get('area') == 'yes':
            return 0
        return 3 if t.get('sac_scale') in MOUNTAIN else 2
    return 0

def route_ways(path):
    """Ids of ways that belong to a waymarked hiking/foot route relation."""
    ids = set()
    for o in osmium.FileProcessor(path).with_filter(osmium.filter.KeyFilter('route')):
        if o.is_relation() and o.tags.get('route') in ('hiking', 'foot'):
            ids.update(m.ref for m in o.members if m.type == 'w')
    return ids

def ele(v):
    m = re.match(r'\s*(-?\d+(?:[.,]\d+)?)', v or '')
    return float(m.group(1).replace(',', '.')) if m else None

def main():
    lat, lon, ln, cat, rt = array('d'), array('d'), array('f'), array('b'), array('b')
    plat, plon, pele = array('d'), array('d'), array('f')
    seen_way, seen_peak = set(), set()
    for f in sorted(glob.glob(os.path.join(OSM, '*-latest.osm.pbf'))):
        t = time.time(); routes = route_ways(f)
        print(f'{os.path.basename(f)}: {len(routes):,} ways in hiking routes ({time.time() - t:.0f} s)', flush=True)
        n0 = len(ln)
        fp = osmium.FileProcessor(f).with_locations().with_filter(osmium.filter.KeyFilter('highway', 'natural'))
        for o in fp:
            if o.is_node():
                if o.tags.get('natural') == 'peak' and o.id not in seen_peak:
                    e = ele(o.tags.get('ele'))
                    if e is not None: plat.append(o.location.lat); plon.append(o.location.lon); pele.append(e); seen_peak.add(o.id)
                continue
            if not o.is_way() or 'highway' not in o.tags or o.id in seen_way: continue
            c = category(o.tags)
            if not c: continue
            pts = [(n.lat, n.lon) for n in o.nodes if n.location.valid()]
            if len(pts) < 2: continue
            seen_way.add(o.id)
            r = 1 if o.id in routes else 0
            p = np.array(pts)
            seg = np.hypot(np.diff(p[:, 0]) * 111195.0, np.diff(p[:, 1]) * 111195.0 * np.cos(np.radians(p[:-1, 0])))
            mid = (p[:-1] + p[1:]) / 2
            lat.extend(mid[:, 0].tolist()); lon.extend(mid[:, 1].tolist()); ln.extend(seg.tolist())
            cat.extend([c] * len(seg)); rt.extend([r] * len(seg))
        print(f'  {len(ln) - n0:,} segments ({time.time() - t:.0f} s)', flush=True)
    L, C, R = np.frombuffer(ln, np.float32), np.frombuffer(cat, np.int8), np.frombuffer(rt, np.int8)
    for c, name in [(1, 'gravel'), (2, 'path'), (3, 'mountain path'), (4, 'rough track')]:
        print(f'{name:14} {L[C == c].sum() / 1000:10,.0f} km, of which in waymarked routes {L[(C == c) & (R == 1)].sum() / 1000:8,.0f} km')
    print(f'peaks with a height: {len(pele):,}')
    np.savez_compressed(os.path.join(WORK, 'features.npz'), lat=np.frombuffer(lat, np.float64).astype(np.float32), lon=np.frombuffer(lon, np.float64).astype(np.float32),
                        length=L, cat=C, route=R, peak_lat=np.frombuffer(plat, np.float64).astype(np.float32),
                        peak_lon=np.frombuffer(plon, np.float64).astype(np.float32), peak_ele=np.frombuffer(pele, np.float32))

if __name__ == '__main__':
    main()
