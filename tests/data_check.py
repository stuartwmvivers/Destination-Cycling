#!/usr/bin/env python3
"""Method-stability check on the BUILT site data (run after build/build_site.py).

1. The HANDOVER 4.4 reference values must come out of _site/data/summary.json unchanged.
2. Every region file must expand back to exactly the rows in data/processed (no values lost or moved).

If (1) fails after a deliberate method or data change, update HANDOVER 4.4 and REFERENCE below together,
and say so in the commit. Usage: python3 tests/data_check.py
"""
import glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(ROOT, *p)
load = lambda p: json.load(open(p, encoding='utf-8'))

# place: (Jan high, Jan low, Jan rideable days, rideable days a year, days >= 30 C a year)   -- HANDOVER 4.4
REFERENCE = {
    'begur': (12.0, 4.4, 12.4, 190.8, 17.6), 'torrox': (16.9, 9.8, 24.0, 294.4, 57.4),
    'nerja': (16.8, 10.0, 22.6, 278.4, 70.4), 'alicante': (16.6, 8.3, 23.6, 263.1, 38.0),
    'palma': (14.8, 8.0, 19.0, 244.9, 71.8), 'pollensa': (14.0, 8.8, 13.8, 212.3, 23.7),
    'dunning': (5.6, 0.8, 0.0, 91.9, 0), 'bristol': (7.4, 2.1, 0.1, 118.2, 1.2),   # Bristol hot: handover said 0; data always gave 1.2
}
fails = []
summary = {p['place']: p['avg'] for p in load(J('_site', 'data', 'summary.json'))['places']}
for place, want in REFERENCE.items():
    a = summary[place]
    got = (a['tmax'][0], a['tmin'][0], a['ride'][0], a['ride'][12], a['hot'][12])
    if any(abs(g - w) > 1e-9 for g, w in zip(got, want)): fails.append(f'{place}: reference {want}, built {got}')

MEASURES = ['tmax', 'tmin', 'rain', 'wet', 'ride', 'warm', 'hot', 'frost', 'tram']
for sub, key in [('climate', 'climate'), ('stations', 'stations')]:
    src = {}
    for f in glob.glob(J('data', 'processed', sub, '*.json')):
        for r in load(f): src[(r['place'], r['year'], r['month'])] = r
    seen = set()
    for f in glob.glob(J('_site', 'data', 'regions', '*.json')):
        d = load(f)
        for place, s in d[key].items():
            ms = s.get('series', s)
            for i in range(len(d['years']) * 12):
                k = (place, d['years'][0] + i // 12, i % 12 + 1)
                vals = {m: ms[m][i] for m in MEASURES}
                if k not in src:
                    if any(v is not None for v in vals.values()): fails.append(f'{f}: {k} has values but no source row')
                    continue
                seen.add(k)
                if vals != {m: src[k][m] for m in MEASURES}: fails.append(f'{f}: {key} {k} differs from data/processed')
                if sub == 'stations':
                    for m in ['source', 'station', 'station_name', 'distance_km', 'elevation_m', 'gust_height_m']:
                        if s[m] != src[k][m]: fails.append(f'{f}: station {k} {m} differs')
    in_places = {p['place'] for p in load(J('config', 'places.json'))}
    missing = {k for k in src if k[0] in in_places} - seen
    if missing: fails.append(f'{sub}: {len(missing)} source rows not in any region file, e.g. {sorted(missing)[:3]}')

if fails:
    print('\n'.join(fails)); sys.exit(1)
print(f'ok: {len(REFERENCE)} reference places match HANDOVER 4.4; region files match data/processed')
