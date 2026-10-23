#!/usr/bin/env python3
"""Fetch daily ERA5-family reanalysis from Open-Meteo and aggregate to monthly cycling measures.

Reproduces the method used to build data/processed/climate/<country>.json (one file per country).
The original run (16-17 Oct 2026) was done from browser JavaScript; this is a faithful
Python port of that logic (see pipeline/openmeteo_browser_reference.js). Verified against
the live API on 23 Oct 2026 (begur, torrox, dunning): temperatures, hot, frost and tram match
the committed rows exactly; rain-based measures differ in a minority of months by 1-2 days,
apparently because Open-Meteo has revised its precipitation since the original fetch.
So a re-fetch will not reproduce the committed rows exactly: run --check first, and if you
write, re-fetch every place together so places stay mutually consistent.

Usage:
  python3 pipeline/openmeteo_fetch.py --check begur   # compare with committed rows, write nothing
  python3 pipeline/openmeteo_fetch.py                 # fetch all places in config/places.json and WRITE
  python3 pipeline/openmeteo_fetch.py begur bristol   # fetch only these place ids and WRITE

Rate limits: the free API allows a limited number of calls per minute/hour/day weighted by
the size of each request (9 years x 5 variables is a heavy request). In the original run,
roughly 5 consecutive requests triggered HTTP 429 "Minutely API request limit exceeded".
This script waits 10 s between places and 65 s after a 429. An empty or non-JSON response
(seen once on 23 Oct 2026) or a network error is retried after 20 s.
"""
import glob, json, math, os, sys, time, urllib.request, urllib.error

def jsround(x, nd=0):
    """Round like JavaScript Math.round (halves go up), which produced the committed data.
    Python's round() uses banker's rounding and would differ in ~5% of months."""
    f = 10 ** nd
    v = math.floor(x * f + 0.5) / f
    return int(v) if nd == 0 else v

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACES = json.load(open(os.path.join(ROOT, 'config', 'places.json'), encoding='utf-8'))
COUNTRY = {p['place']: p['country'] for p in PLACES}
OUT_DIR = os.path.join(ROOT, 'data', 'processed', 'climate')
START, END = '2017-01-01', '2025-12-31'
VARS = 'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_gusts_10m_max,wind_direction_10m_dominant'
MEASURES = ['tmax', 'tmin', 'rain', 'wet', 'ride', 'warm', 'hot', 'frost', 'tram']
# NB: every place, including the UK ones, was fetched with timezone=Europe/Madrid so that
# day boundaries are consistent. Keep this unless you re-fetch everything.
TZ = 'Europe%2FMadrid'

def fetch(lat, lon):
    url = (f'https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}'
           f'&start_date={START}&end_date={END}&daily={VARS}&timezone={TZ}')
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print('  rate-limited, waiting 65 s', flush=True); time.sleep(65); continue
            raise
        except (json.JSONDecodeError, urllib.error.URLError, TimeoutError) as e:
            print(f'  bad or empty response ({type(e).__name__}), retrying in 20 s', flush=True); time.sleep(20)
    raise RuntimeError('no valid response after 6 attempts')

def monthly(place_id, daily):
    """Aggregate daily values to the 9 monthly measures. Thresholds are part of the method;
    changing them changes every number on the site."""
    gaps = {k: sum(v is None for v in vals) for k, vals in daily.items() if k != 'time'}
    assert not any(gaps.values()), f'{place_id}: missing daily values {gaps}'
    M = {}
    for i, t in enumerate(daily['time']):
        y, m = int(t[:4]), int(t[5:7])
        a = M.setdefault((y, m), dict(n=0, tx=0.0, tn=0.0, r=0.0, wet=0, ride=0, comf=0, hot=0, fr=0, tram=0))
        tx = daily['temperature_2m_max'][i]; tn = daily['temperature_2m_min'][i]
        p = daily['precipitation_sum'][i]; g = daily['wind_gusts_10m_max'][i]; d = daily['wind_direction_10m_dominant'][i]
        a['n'] += 1; a['tx'] += tx; a['tn'] += tn; a['r'] += p
        if p >= 1: a['wet'] += 1
        calm, dry = g < 50, p < 1                      # gusts in km/h
        if tx >= 11 and dry and calm: a['ride'] += 1   # "rideable day"
        if 14 <= tx <= 30 and dry and calm: a['comf'] += 1  # "warm riding day"
        if tx >= 30: a['hot'] += 1
        if tn <= 0: a['fr'] += 1
        if g >= 50 and (d >= 290 or d <= 40): a['tram'] += 1  # north / north-west gale ("north-wind day")
    rows = []
    for (y, m), a in sorted(M.items()):
        rows.append({'place': place_id, 'year': y, 'month': m,
                     'tmax': jsround(a['tx'] / a['n'], 1), 'tmin': jsround(a['tn'] / a['n'], 1),
                     'rain': jsround(a['r']), 'wet': a['wet'], 'ride': a['ride'], 'warm': a['comf'],
                     'hot': a['hot'], 'frost': a['fr'], 'tram': a['tram']})
    return rows

def compare(place_id, old_rows, new_rows):
    """Print how freshly fetched rows differ from the committed ones, per measure and as 9-year averages."""
    old = {(r['year'], r['month']): r for r in old_rows}
    new = {(r['year'], r['month']): r for r in new_rows}
    if set(old) != set(new):
        print(f'  months differ: {len(old)} committed, {len(new)} fetched'); return
    n_years = len({y for y, _ in old})
    total = 0
    for f in MEASURES:
        ds = [new[k][f] - old[k][f] for k in sorted(old) if new[k][f] != old[k][f]]
        total += len(ds)
        o = sum(r[f] for r in old.values()) / n_years; n = sum(r[f] for r in new.values()) / n_years
        if f in ('tmax', 'tmin'): o, n = o / 12, n / 12   # temperatures: mean of monthly means
        line = f'  {f:5} {len(ds):3} months differ' + (f', max |diff| {max(map(abs, ds)):g}' if ds else '')
        print(f'{line:42} 9-yr avg per year: committed {o:.1f}, live {n:.1f}')
    print(f'  {total} of {len(old) * len(MEASURES)} values differ')

def main(ids, check):
    files = sorted(glob.glob(os.path.join(OUT_DIR, '*.json')))
    existing = [r for f in files for r in json.load(open(f, encoding='utf-8'))]
    keep = [r for r in existing if r['place'] not in ids]
    new = []
    for p in PLACES:
        if p['place'] not in ids: continue
        j = fetch(p['lat'], p['lon'])
        assert j['daily']['time'][0] == START and len(j['daily']['time']) == 3287, 'unexpected day count'
        rows = monthly(p['place'], j['daily'])
        assert len(rows) == 108
        new += rows
        print(p['place'], 'grid point', j['latitude'], j['longitude'], 'elev', j['elevation'], flush=True)
        if check:
            compare(p['place'], [r for r in existing if r['place'] == p['place']], rows)
        time.sleep(10)
    if check:
        print('check only: nothing written'); return
    by_country = {}
    for r in keep + new: by_country.setdefault(COUNTRY[r['place']], []).append(r)
    for c, rows in sorted(by_country.items()):
        json.dump(rows, open(os.path.join(OUT_DIR, f'{c}.json'), 'w', encoding='utf-8'), separators=(',', ':'))
        print('wrote', len(rows), 'rows to', f'data/processed/climate/{c}.json')

if __name__ == '__main__':
    args = sys.argv[1:]
    check = '--check' in args
    ids = [a for a in args if a != '--check'] or [p['place'] for p in PLACES]
    unknown = set(ids) - {p['place'] for p in PLACES}
    if unknown: sys.exit(f'unknown place id(s): {", ".join(sorted(unknown))}')
    main(ids, check)
