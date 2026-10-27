#!/usr/bin/env python3
"""Municipality of every base, for property prices (phase 6; docs/price-data-plan.md).

Municipal boundaries are OSM boundary=administrative, admin_level=8 areas, with the INE municipality code
(`ine:municipio`) where tagged. Each base takes the municipality it lies in (or the nearest within 2 km, for a point
just offshore or on a boundary gap).
Output: WORK/municipalities.json: {'munis': [{id, name, ine, lat, lon}], 'base_muni': [index per base in
data/processed/score/spain.json order, or -1]}.
Usage (score venv): python pipeline/score/municipalities.py
"""
import glob, json, os, time
import numpy as np
import osmium, shapely
from shapely import wkb
from common import OSM, ROOT, WORK

def main():
    t = time.time()
    fab = osmium.geom.WKBFactory()
    names, ines, geoms = [], [], []
    for f in sorted(glob.glob(os.path.join(OSM, '*-latest.osm.pbf'))):
        fp = osmium.FileProcessor(f).with_areas(osmium.filter.TagFilter(('boundary', 'administrative')))
        for o in fp:
            if not isinstance(o, osmium.osm.Area) or o.tags.get('admin_level') != '8' or o.from_way(): continue
            try: g = wkb.loads(fab.create_multipolygon(o), hex=True)
            except Exception: continue
            names.append(o.tags.get('name', '')); ines.append(o.tags.get('ine:municipio', '')); geoms.append(g)
        print(f'{os.path.basename(f)}: {len(geoms):,} municipalities so far ({time.time() - t:.0f} s)', flush=True)
    tree = shapely.STRtree(geoms)
    B = json.load(open(os.path.join(ROOT, 'data', 'processed', 'score', 'spain.json'), encoding='utf-8'))['bases']
    pts = shapely.points(np.array(B['lon']), np.array(B['lat']))
    base_muni = np.full(len(pts), -1)
    hit_pt, hit_geom = tree.query(pts, predicate='within')
    base_muni[hit_pt] = hit_geom
    miss = np.flatnonzero(base_muni < 0)
    if len(miss):
        idx, dist = tree.query_nearest(pts[miss], max_distance=0.02, return_distance=True, all_matches=False)
        base_muni[miss[idx[0]]] = idx[1]
    c = shapely.centroid(geoms)
    out = {'munis': [{'id': i, 'name': n, 'ine': k, 'lat': round(float(p.y), 4), 'lon': round(float(p.x), 4)}
                     for i, (n, k, p) in enumerate(zip(names, ines, c))],
           'base_muni': [int(x) for x in base_muni]}
    json.dump(out, open(os.path.join(WORK, 'municipalities.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{len(geoms):,} municipalities ({sum(1 for k in ines if k):,} with an INE code); '
          f'{(base_muni >= 0).sum():,} of {len(pts):,} bases placed ({time.time() - t:.0f} s)')

if __name__ == '__main__':
    main()
