#!/usr/bin/env python3
"""Combine aggregated Meteocat + AEMET station months into data/processed/stations/<country>.json.
Inputs: data/interim/stations_monthly.json (meteocat_aggregate.py), data/interim/aemet_monthly.json
(aemet_aggregate.py), data/raw/meteocat/stations.json (meteocat_fetch.py), data/reference/aemet-station-inventory.json.
"""
import json, math, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(ROOT, *p)
load = lambda *p, enc='utf-8': json.load(open(J(*p), encoding=enc))
places = {p['place']: p for p in load('config', 'places.json')}
km = lambda la, lo, p: round(math.hypot((la - p['lat']) * 111, (lo - p['lon']) * 111 * math.cos(math.radians(la))), 1)
FIELDS = ['tmax', 'tmin', 'rain', 'wet', 'ride', 'warm', 'hot', 'frost', 'tram']
rows = []
mc_meta = {s['codi']: s for s in load('data', 'raw', 'meteocat', 'stations.json')}
for code, rs in load('data', 'interim', 'stations_monthly.json').items():
    s = mc_meta[code]; p = places[rs[0]['place']]
    d = km(s['coordenades']['latitud'], s['coordenades']['longitud'], p)
    for r in rs:
        o = {'place': r['place'], 'source': 'Meteocat', 'station': code, 'station_name': s['nom'], 'distance_km': d,
             'elevation_m': s['altitud'], 'gust_height_m': r['gust_height'], 'year': r['year'], 'month': r['month']}
        o.update({k: r.get(k) for k in FIELDS}); rows.append(o)
inv = {s['indicativo']: s for s in load('data', 'reference', 'aemet-station-inventory.json', enc='latin-1')}
NICE = {'6213X': 'Nerja', '6205X': 'Torrox', '6076X': 'Marbella Puerto', '6058I': 'Estepona', '8025': 'Alicante', '8036Y': 'Benidorm',
        '8050X': 'Xàbia', 'B228': 'Palma Puerto', 'B051A': 'Port de Sóller', 'B760X': 'Pollença'}
def dms(v):
    x = int(v[:2]) + int(v[2:4]) / 60 + int(v[4:6]) / 3600
    return -x if v[-1] in 'WS' else x
for code, o in load('data', 'interim', 'aemet_monthly.json').items():
    s = inv[code]; p = places[o['rows'][0]['place']]
    d = km(dms(s['latitud']), dms(s['longitud']), p)
    for r in o['rows']:
        x = {'place': r['place'], 'source': 'AEMET', 'station': code, 'station_name': NICE[code], 'distance_km': d,
             'elevation_m': o['elev'], 'gust_height_m': 10 if o['wind'] else None, 'year': r['year'], 'month': r['month']}
        x.update({k: r.get(k) for k in FIELDS}); rows.append(x)
by_country = {}
for r in rows: by_country.setdefault(places[r['place']]['country'], []).append(r)
for c, rs in by_country.items():
    json.dump(rs, open(J('data', 'processed', 'stations', f'{c}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(c, len(rs), 'rows')
