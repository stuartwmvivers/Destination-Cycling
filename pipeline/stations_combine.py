#!/usr/bin/env python3
"""Combine aggregated station months (Meteocat, AEMET, Met Office MIDAS) into data/processed/stations/<country>.json.

Each source is rebuilt only if its inputs are present; rows from other sources are kept exactly as committed
(their raw data are git-ignored and may not be on this machine). Country files are rewritten only if they change.
Inputs, per source:
  Meteocat:   data/interim/stations_monthly.json (meteocat_aggregate.py), data/raw/meteocat/stations.json (meteocat_fetch.py)
  AEMET:      data/interim/aemet_monthly.json (aemet_aggregate.py), data/reference/aemet-station-inventory.json
  Met Office: data/interim/midas_monthly.json (midas_aggregate.py)
Met Office rows pair two stations (temperature + wind, and a rain gauge): station, station_name, distance_km and
elevation_m describe the first; rain_station, rain_station_name, rain_distance_km and rain_elevation_m the second.
"""
import glob, json, math, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(ROOT, *p)
load = lambda *p, enc='utf-8': json.load(open(J(*p), encoding=enc))
have = lambda *p: os.path.exists(J(*p))
places = {p['place']: p for p in load('config', 'places.json')}
km = lambda la, lo, p: round(math.hypot((la - p['lat']) * 111, (lo - p['lon']) * 111 * math.cos(math.radians(la))), 1)
FIELDS = ['tmax', 'tmin', 'rain', 'wet', 'ride', 'warm', 'hot', 'frost', 'tram']

def meteocat():
    rows = []
    mc_meta = {s['codi']: s for s in load('data', 'raw', 'meteocat', 'stations.json')}
    for code, rs in load('data', 'interim', 'stations_monthly.json').items():
        s = mc_meta[code]; p = places[rs[0]['place']]
        d = km(s['coordenades']['latitud'], s['coordenades']['longitud'], p)
        for r in rs:
            o = {'place': r['place'], 'source': 'Meteocat', 'station': code, 'station_name': s['nom'], 'distance_km': d,
                 'elevation_m': s['altitud'], 'gust_height_m': r['gust_height'], 'year': r['year'], 'month': r['month']}
            o.update({k: r.get(k) for k in FIELDS}); rows.append(o)
    return rows

def aemet():
    rows = []
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
    return rows

def midas():
    rows = []
    for place, o in load('data', 'interim', 'midas_monthly.json').items():
        p, tw, rn = places[place], o['tw'], o['rain']
        info = {'place': place, 'source': 'Met Office', 'station': tw['code'], 'station_name': tw['name'], 'distance_km': km(tw['lat'], tw['lon'], p),
                'elevation_m': tw['elev'], 'gust_height_m': 10, 'rain_station': rn['code'], 'rain_station_name': rn['name'],
                'rain_distance_km': km(rn['lat'], rn['lon'], p), 'rain_elevation_m': rn['elev']}
        for r in o['rows']:
            rows.append({**info, 'year': r['year'], 'month': r['month'], **{k: r.get(k) for k in FIELDS}})
    return rows

SOURCES = {'Meteocat': (meteocat, [('data', 'interim', 'stations_monthly.json'), ('data', 'raw', 'meteocat', 'stations.json')]),
           'AEMET': (aemet, [('data', 'interim', 'aemet_monthly.json')]),
           'Met Office': (midas, [('data', 'interim', 'midas_monthly.json')])}
existing = {os.path.basename(f)[:-5]: json.load(open(f, encoding='utf-8')) for f in glob.glob(J('data', 'processed', 'stations', '*.json'))}
rows = [r for rs in existing.values() for r in rs]
for name, (build, inputs) in SOURCES.items():
    if all(have(*i) for i in inputs):
        rows = [r for r in rows if r['source'] != name] + build()
        print('rebuilt', name)
    else:
        print('kept committed rows for', name, '(inputs not present)')
by_country = {}
for r in rows: by_country.setdefault(places[r['place']]['country'], []).append(r)
for c, rs in sorted(by_country.items()):
    if rs == existing.get(c):
        print(c, len(rs), 'rows, unchanged'); continue
    json.dump(rs, open(J('data', 'processed', 'stations', f'{c}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(c, len(rs), 'rows written')
