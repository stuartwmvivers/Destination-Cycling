#!/usr/bin/env python3
"""Eating out, from the OSM extracts in the cache (docs/interface-plan.md, "Eating out"; owner, 29 October 2026).

Shown as a fact, not scored. The owner's test is walking distance to a cluster of restaurants, so this finds
"eating-out centres" rather than counting places per area:
  1. every amenity=restaurant, cafe, bar, pub or biergarten (nodes, and buildings drawn as ways, at their middle);
  2. a centre is where at least MIN_N of them lie within WALK_M of a point (straight line; about a 10-minute walk
     once streets wind), found greedily from the densest place, re-centred on its neighbours, at least SEP_M apart.
     MIN_N is low (a village with a bar and a couple of restaurants counts) because the owner leans rural, and
     because OSM under-maps small towns (Loja: 7 mapped within 600 m), so counts are "at least";
  3. each centre is named after the nearest town, village or district (OSM place nodes).
Output: WORK/eating.json.  Usage (score venv, DC_CACHE set): python pipeline/score/extract_eating.py
"""
import glob, json, math, os, time
import numpy as np, osmium
from scipy.spatial import cKDTree
from common import OSM, WORK

KINDS = {'restaurant': 'r', 'cafe': 'c', 'bar': 'b', 'pub': 'b', 'biergarten': 'b'}
WALK_M, MIN_N, SEP_M = 600, 3, 1000
TOWN = {'city', 'town', 'village'}; DISTRICT = {'suburb', 'quarter', 'neighbourhood', 'hamlet'}
M = 111195.0

def xy(lat, lon):
    # metres on a plane, each point scaled by its own latitude: right within a walk, which is all that's measured
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    return np.column_stack([lon * M * np.cos(np.radians(lat)), lat * M])

def read(f):
    pois, places = [], []
    fp = osmium.FileProcessor(f).with_locations().with_filter(osmium.filter.KeyFilter('amenity', 'place'))
    for o in fp:
        tg = o.tags; k = KINDS.get(tg.get('amenity'))
        if o.is_node() and not k:
            p = tg.get('place')
            if (p in TOWN or p in DISTRICT) and tg.get('name') and o.location.valid():
                places.append((o.location.lat, o.location.lon, tg['name'], p))
            continue
        if not k: continue
        if o.is_node():
            if o.location.valid(): pois.append((o.location.lat, o.location.lon, k))
        elif o.is_way():
            pts = [(n.lat, n.lon) for n in o.nodes if n.location.valid()]
            if pts: pois.append((sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), k))
    return pois, places

def centres(pois, places):
    lat = np.array([p[0] for p in pois]); lon = np.array([p[1] for p in pois]); kind = np.array([p[2] for p in pois])
    P = xy(lat, lon); tree = cKDTree(P)
    dens = np.array([len(x) for x in tree.query_ball_point(P, WALK_M)])
    out, taken = [], []
    for i in np.argsort(-dens):
        if dens[i] < MIN_N: break
        c = P[tree.query_ball_point(P[i], WALK_M)].mean(axis=0)      # re-centre on the cluster
        near = tree.query_ball_point(c, WALK_M)
        if len(near) < MIN_N or any(math.dist(c, t) < SEP_M for t in taken): continue
        taken.append(c)
        k = kind[near]
        out.append({'xy': c, 'n': len(near), 'r': int((k == 'r').sum()), 'c': int((k == 'c').sum()), 'b': int((k == 'b').sum())})
    # names: the nearest district within 700 m (with its town), else the nearest town or village within 1.5 km, else "near" one
    pl = places; Q = xy([p[0] for p in pl], [p[1] for p in pl])
    town_ix = [j for j, p in enumerate(pl) if p[3] in TOWN]; Tt = cKDTree(Q[town_ix]); Ta = cKDTree(Q)
    for c in out:
        dt, jt = Tt.query(c['xy']); town = pl[town_ix[jt]]
        name = town[2] if dt <= 1500 else f'near {town[2]}'
        for d, j in zip(*Ta.query(c['xy'], k=4)):
            if d > 700: break
            if pl[j][3] in DISTRICT and pl[j][2] != town[2] and dt > 300:
                name = f'{pl[j][2]}, {town[2]}' if dt <= 6000 else pl[j][2]
                break
        c['name'] = name
        la = c['xy'][1] / M; c['lat'] = round(la, 5); c['lon'] = round(c['xy'][0] / (M * math.cos(math.radians(la))), 5)
        del c['xy']
    return out

def main():
    allc, total = [], 0
    for f in sorted(glob.glob(os.path.join(OSM, '*-latest.osm.pbf'))):
        t = time.time(); pois, places = read(f)
        cs = centres(pois, places); allc += cs; total += len(pois)
        print(f'{os.path.basename(f)}: {len(pois):,} places to eat and drink, {len(places):,} place names, '
              f'{len(cs):,} eating-out centres ({time.time() - t:.0f} s)', flush=True)
    allc.sort(key=lambda c: -c['n'])
    src = {os.path.basename(f): time.strftime('%Y-%m-%d', time.gmtime(os.path.getmtime(f))) for f in glob.glob(os.path.join(OSM, '*-latest.osm.pbf'))}
    json.dump({'walk_m': WALK_M, 'min_n': MIN_N, 'sep_m': SEP_M, 'osm': src, 'pois': total, 'centres': allc},
              open(os.path.join(WORK, 'eating.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    for c in allc[:8]: print(f"  {c['n']:>4}  {c['name']}")

if __name__ == '__main__':
    main()
