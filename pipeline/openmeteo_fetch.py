#!/usr/bin/env python3
"""Fetch daily ERA5-family reanalysis from Open-Meteo and aggregate to monthly cycling measures.

Reproduces the method used to build data/processed/climate-spain-2017-2025.json.
The original run (16-17 Oct 2026) was done from browser JavaScript; this is a faithful
Python port of that logic (see pipeline/openmeteo_browser_reference.js). It has NOT yet
been run end-to-end from Python, so on first use, re-fetch one existing place (e.g. begur)
and diff against the committed file before trusting it for new places.

Usage:
  python3 pipeline/openmeteo_fetch.py                 # all places in pipeline/places.json
  python3 pipeline/openmeteo_fetch.py begur bristol   # only these place ids

Rate limits: the free API allows a limited number of calls per minute/hour/day weighted by
the size of each request (9 years x 5 variables is a heavy request). In the original run,
roughly 5 consecutive requests triggered HTTP 429 "Minutely API request limit exceeded".
This script waits 10 s between places and 65 s after a 429.
"""
import json, math, os, sys, time, urllib.request, urllib.error

def jsround(x, nd=0):
    """Round like JavaScript Math.round (halves go up), which produced the committed data.
    Python's round() uses banker's rounding and would differ in ~5% of months."""
    f = 10 ** nd
    v = math.floor(x * f + 0.5) / f
    return int(v) if nd == 0 else v

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACES = json.load(open(os.path.join(ROOT, 'pipeline', 'places.json')))
OUT = os.path.join(ROOT, 'data', 'processed', 'climate-spain-2017-2025.json')
START, END = '2017-01-01', '2025-12-31'
VARS = 'temperature_2m_max,temperature_2m_min,precipitation_sum,wind_gusts_10m_max,wind_direction_10m_dominant'
# NB: every place, including the UK ones, was fetched with timezone=Europe/Madrid so that
# day boundaries are consistent. Keep this unless you re-fetch everything.
TZ = 'Europe%2FMadrid'

def fetch(lat, lon):
    url = (f'https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}'
           f'&start_date={START}&end_date={END}&daily={VARS}&timezone={TZ}')
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(65); continue
            raise
    raise RuntimeError('rate-limited too many times')

def monthly(place_id, daily):
    """Aggregate daily values to the 9 monthly measures. Thresholds are part of the method;
    changing them changes every number on the site."""
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

def main(ids):
    existing = json.load(open(OUT)) if os.path.exists(OUT) else []
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
        time.sleep(10)
    json.dump(keep + new, open(OUT, 'w'), separators=(',', ':'))
    print('wrote', len(keep + new), 'rows')

if __name__ == '__main__':
    ids = sys.argv[1:] or [p['place'] for p in PLACES]
    main(ids)
