#!/usr/bin/env python3
"""Cycling facilities near each mock-up area (trial, 5 Nov 2026). Not part of the site build.

Asks OpenStreetMap (Overpass API) for bike shops, bike hire and public repair stations within RADIUS km of each
area in mockup/data/areas.json and writes mockup/data/facilities.json, keyed by area id: counts plus the nearest
shops and hire places with name, distance, whether they hire or repair, and website if tagged. Hire points
sharing a name (a bike-share scheme's docks) count once, with the number of points.
OpenStreetMap data (c) OpenStreetMap contributors, ODbL. Coverage depends on local mappers, so absence is not proof.
Usage: python mockup/make_facilities.py
"""
import json, math, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'data')
RADIUS, KEEP = 15, 8
UA = {'User-Agent': 'DestinationCycling-mockup/0.1 (https://github.com/stuartwmvivers/Destination-Cycling)'}

def overpass(q):
    for i in range(5):
        try:
            req = urllib.request.Request('https://overpass-api.de/api/interpreter', data=urllib.parse.urlencode({'data': q}).encode(), headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)['elements']
        except Exception as e:
            print('  retry:', e, file=sys.stderr); time.sleep(15 * (i + 1))
    raise RuntimeError('overpass failed')

def km(a, b, c, d):
    return math.hypot((a - c) * 111.2, (b - d) * 111.2 * math.cos(math.radians(a)))

def main():
    areas = json.load(open(os.path.join(OUT, 'areas.json'), encoding='utf-8'))['areas']
    path = os.path.join(OUT, 'facilities.json')
    out = json.load(open(path, encoding='utf-8'))['areas'] if os.path.exists(path) else {}
    for a in areas:
        if a['id'] in out: continue
        la, lo, r = a['lat'], a['lon'], RADIUS * 1000
        els = overpass(f'''[out:json][timeout:120];
(nwr(around:{r},{la},{lo})[shop=bicycle];
 nwr(around:{r},{la},{lo})[amenity=bicycle_rental];
 nwr(around:{r},{la},{lo})["service:bicycle:rental"=yes];
 nwr(around:{r},{la},{lo})[amenity=bicycle_repair_station];);
out tags center;''')
        shops, hire, stations = [], [], 0
        for e in els:
            t = e.get('tags', {}); c = e.get('center') or {'lat': e.get('lat'), 'lon': e.get('lon')}
            if c['lat'] is None: continue
            if t.get('amenity') == 'bicycle_repair_station':
                stations += 1; continue
            row = {'name': t.get('name') or t.get('brand') or t.get('operator'), 'km': round(km(la, lo, c['lat'], c['lon']), 1),
                   'hire': t.get('amenity') == 'bicycle_rental' or t.get('service:bicycle:rental') == 'yes',
                   'repair': t.get('service:bicycle:repair') == 'yes', 'web': t.get('website') or t.get('contact:website')}
            if t.get('shop') == 'bicycle': row['kind'] = 'shop'; shops.append(row)
            elif row['hire']: row['kind'] = 'hire'; hire.append(row)
        # hire points with the same name (a bike-share scheme's docks) are one entry, nearest first, with a count;
        # unnamed hire points count once in total and are not listed
        groups = {}
        for h in sorted(hire, key=lambda x: x['km']):
            if not h['name']: continue
            g = groups.setdefault(h['name'].lower(), {**h, 'points': 0}); g['points'] += 1
        near = sorted(shops + list(groups.values()), key=lambda x: x['km'])[:KEEP]
        out[a['id']] = {'shops': len(shops), 'hire': sum(1 for s in shops if s['hire']) + len(groups) + any(not h['name'] for h in hire),
                        'repair_stations': stations, 'near': near}
        print(f"{a['name']}: {len(shops)} shops, {out[a['id']]['hire']} hire, {stations} repair stations", file=sys.stderr)
        json.dump({'radius_km': RADIUS, 'source': 'OpenStreetMap via Overpass API', 'fetched': time.strftime('%Y-%m-%d'), 'areas': out},
                  open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(3)

if __name__ == '__main__':
    main()
