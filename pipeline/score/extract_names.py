#!/usr/bin/env python3
"""Names for the score page, from the OSM extracts in the cache, so bases and climbs can be labelled:
  places   place=city/town/village nodes with a name (and population where tagged)
  passes   named mountain_pass=yes or natural=saddle nodes, and named peaks (natural=peak), for climb tops
Output: WORK/names.json.  Usage (score venv): python pipeline/score/extract_names.py
"""
import glob, json, os, time
import osmium
from common import OSM, WORK

PLACE_RANK = {'city': 3, 'town': 2, 'village': 1}

def main():
    places, passes = [], []
    for f in sorted(glob.glob(os.path.join(OSM, '*-latest.osm.pbf'))):
        t = time.time()
        fp = osmium.FileProcessor(f, osmium.osm.NODE).with_filter(osmium.filter.KeyFilter('place', 'mountain_pass', 'natural'))
        for o in fp:
            tg = o.tags; name = tg.get('name')
            if not name or not o.location.valid(): continue
            la, lo = round(o.location.lat, 5), round(o.location.lon, 5)
            if tg.get('place') in PLACE_RANK:
                try: pop = int(tg.get('population', '').replace('.', '').replace(',', '').strip())
                except ValueError: pop = None
                places.append({'name': name, 'lat': la, 'lon': lo, 'rank': PLACE_RANK[tg['place']], 'pop': pop})
            elif tg.get('mountain_pass') == 'yes' or tg.get('natural') == 'saddle':
                passes.append({'name': name, 'lat': la, 'lon': lo, 'kind': 'pass'})
            elif tg.get('natural') == 'peak':
                passes.append({'name': name, 'lat': la, 'lon': lo, 'kind': 'peak'})
        print(f'{os.path.basename(f)}: {len(places):,} places, {len(passes):,} passes and peaks so far ({time.time() - t:.0f} s)', flush=True)
    json.dump({'places': places, 'passes': passes}, open(os.path.join(WORK, 'names.json'), 'w', encoding='utf-8'), ensure_ascii=False)

if __name__ == '__main__':
    main()
