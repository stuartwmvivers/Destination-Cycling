#!/usr/bin/env python3
"""Aggregate MIDAS Open station files (from midas_fetch.py) to the nine monthly measures.

Same thresholds and completeness rule as the Spanish stations (HANDOVER 4.2 / 5.3): a measure is valid
for a month only if >= 90% of its days are present; ride/warm need temperature, rain and gust on the
same day; Python round() (as the other station scripts). MIDAS specifics:
- Temperature: max from the 12-hour reading ending 21:00 (09-21 UTC), min from the 12-hour reading
  ending 09:00 (21-09 UTC), both credited to that day (Met Office convention). The rare 24-hour
  readings fill gaps: max from 09-09 credited to the day it starts, min from the one ending that day.
- Rain: 09-09 UTC totals credited to the day the period starts (MIDAS ob_date is the end date; checked
  against modelled Dunning rain on 24 Oct 2026: r 0.61 shifted vs 0.53 unshifted). Multi-day totals
  are ignored. Where a site has two gauges (Kinkell Bridge), the one with most daily records is used.
- Gusts: hourly max gusts in knots x 1.852 -> km/h; a day's gust is the highest of its UTC hours
  (needs >= 19 of 24 hours), and its direction is that gust's direction, as for Meteocat (5.3).
Output: data/interim/midas_monthly.json, one entry per place, for stations_combine.py.
"""
import calendar, csv, glob, io, json, os
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from midas_fetch import ROOT, STATIONS, YEARS
RAW = os.path.join(ROOT, 'data', 'raw', 'midas')
KNOT = 1.852

def read(ds, station):
    """(header fields, data rows) for every downloaded yearly file of a station."""
    head, rows = {}, []
    for f in sorted(glob.glob(os.path.join(RAW, ds, f'*_{station}_qcv-1_*.csv'))):
        text = open(f, encoding='utf-8').read()
        top, body = text.split('\ndata\n', 1)
        for line in top.split('\n'):
            p = line.split(',')
            if len(p) > 2 and p[1] == 'G' and p[0] in ('observation_station', 'location', 'height'): head[p[0]] = p[2:]
        rows += csv.DictReader(io.StringIO(body.rsplit('\nend data', 1)[0]))
    return head, rows

num = lambda v: None if v in ('NA', '', None) else float(v)

def temperatures(station):
    head, rows = read('uk-daily-temperature-obs', station)
    tx, tn, tx24, tn24 = {}, {}, {}, {}
    for r in rows:
        t = datetime.fromisoformat(r['ob_end_time']); d = t.date()
        if r['ob_hour_count'] == '12' and t.hour == 21 and num(r['max_air_temp']) is not None: tx[d] = num(r['max_air_temp'])
        if r['ob_hour_count'] == '12' and t.hour == 9 and num(r['min_air_temp']) is not None: tn[d] = num(r['min_air_temp'])
        if r['ob_hour_count'] == '24' and t.hour == 9:
            if num(r['max_air_temp']) is not None: tx24[d - timedelta(days=1)] = num(r['max_air_temp'])
            if num(r['min_air_temp']) is not None: tn24[d] = num(r['min_air_temp'])
    return head, {**tx24, **tx}, {**tn24, **tn}

def rain(station):
    head, rows = read('uk-daily-rain-obs', station)
    daily = [r for r in rows if r['ob_day_cnt'] == '1' and num(r['prcp_amt']) is not None]
    main = Counter(r['id'] for r in daily).most_common(1)[0][0] if daily else None
    p = {date.fromisoformat(r['ob_date'][:10]) - timedelta(days=1): num(r['prcp_amt']) for r in daily if r['id'] == main}
    return head, p, main

def gusts(station):
    head, rows = read('uk-mean-wind-obs', station)
    hours = defaultdict(list)
    for r in rows:
        g = num(r['max_gust_speed'])
        if r['ob_hour_count'] == '1' and g is not None:
            hours[(datetime.fromisoformat(r['ob_end_time']) - timedelta(hours=1)).date()].append((g * KNOT, num(r['max_gust_dir'])))
    best = {d: max(hs, key=lambda x: x[0]) for d, hs in hours.items() if len(hs) >= 19}
    return head, {d: g for d, (g, _) in best.items()}, {d: dr for d, (_, dr) in best.items()}

def monthly(tx, tn, pr, gu, di):
    rows = []
    for y in YEARS:
        for m in range(1, 13):
            nd = calendar.monthrange(y, m)[1]
            days = [date(y, m, d) for d in range(1, nd + 1)]
            r = {'year': y, 'month': m}
            T = [d for d in days if d in tx and d in tn]
            if len(T) >= 0.9 * nd:
                r['tmax'] = round(sum(tx[d] for d in T) / len(T), 1); r['tmin'] = round(sum(tn[d] for d in T) / len(T), 1)
                r['hot'] = sum(1 for d in T if tx[d] >= 30); r['frost'] = sum(1 for d in T if tn[d] <= 0)
            P = [d for d in days if d in pr]
            if len(P) >= 0.9 * nd:
                r['rain'] = round(sum(pr[d] for d in P)); r['wet'] = sum(1 for d in P if pr[d] >= 1)
            G = [d for d in days if d in gu]
            if len(G) >= 0.9 * nd:
                r['tram'] = sum(1 for d in G if gu[d] >= 50 and di[d] is not None and (di[d] >= 290 or di[d] <= 40))
            if 'tmax' in r and 'rain' in r and 'tram' in r:
                B = [d for d in days if d in tx and d in pr and d in gu]
                r['ride'] = sum(1 for d in B if tx[d] >= 11 and pr[d] < 1 and gu[d] < 50)
                r['warm'] = sum(1 for d in B if 14 <= tx[d] <= 30 and pr[d] < 1 and gu[d] < 50)
            rows.append(r)
    return rows

def site(head, code):
    lat, lon = (float(x) for x in head['location'][:2])
    return {'code': code.split('_')[0], 'name': head['observation_station'][0].replace('-', ' ').title(), 'lat': lat, 'lon': lon, 'elev': float(head['height'][0])}

out = {}
for place, roles in STATIONS.items():
    tw, rn = roles['tw'][1], roles['rain'][1]
    ht, tx, tn = temperatures(tw)
    hw, gu, di = gusts(tw)
    hr, pr, gauge = rain(rn)
    rows = monthly(tx, tn, pr, gu, di)
    out[place] = {'tw': site(ht or hw, tw), 'rain': {**site(hr, rn), 'gauge_id': gauge}, 'rows': rows}
    print(f"{place:8} {out[place]['tw']['name']} + {out[place]['rain']['name']} (gauge {gauge}): months with temp {sum('tmax' in r for r in rows)},"
          f" rain {sum('rain' in r for r in rows)}, gust {sum('tram' in r for r in rows)}, ride {sum('ride' in r for r in rows)} of {len(rows)}")
os.makedirs(os.path.join(ROOT, 'data', 'interim'), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, 'data', 'interim', 'midas_monthly.json'), 'w', encoding='utf-8'), ensure_ascii=False)
