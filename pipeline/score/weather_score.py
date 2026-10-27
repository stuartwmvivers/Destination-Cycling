#!/usr/bin/env python3
"""Weather component for each base with at least MIN_NEAR near climb (spec section 3): rideable days measured at the height of its
climbs, weighted to the months a holiday home would be used.

- Bases: MIN_NEAR = 1, not the gate's 3, so the score page can relax the gate (spec 7a). Weather points were chosen
  for gate-passing areas only (weather_points.py), so bases with 1-2 near climbs often borrow a neighbour's point.
- Weather: the base's own weather point (weather_points.py), or the nearest point fetched so far.
- Climb height: the median of the mid-heights ((foot + top) / 2) of the base's near climbs.
- Temperature: the day's high adjusted from the model's grid-cell height to the climb height at LAPSE degrees per km
  (rain and gusts are left as they are, as Open-Meteo itself does).
- Rideable day: exactly HANDOVER 4.2: high >= 11 C, precipitation < 1 mm, max gust < 50 km/h.
- Index: rideable days per month (2017-2025 average), then a weighted mean of the monthly rideable share with
  October-May at 1.0 and June-September at SUMMER_W.
Output: WORK/weather_bases.json. Usage (score venv): python pipeline/score/weather_score.py [--check]
"""
import datetime as dt, glob, json, math, os, sys
import numpy as np
from common import WORK

LAPSE = 6.5            # C per 1000 m
SUMMER_W = 0.25        # weight of June-September against October-May
MIN_NEAR = 1
MONTH_W = np.array([1, 1, 1, 1, 1, SUMMER_W, SUMMER_W, SUMMER_W, SUMMER_W, 1, 1, 1], float)

def day_months():
    d0 = dt.date(2017, 1, 1)
    days = [d0 + dt.timedelta(days=i) for i in range(3287)]
    return np.array([d.month for d in days]), np.array([d.year for d in days])

def main(check):
    climbs = json.load(open(os.path.join(WORK, 'climbs.json')))['climbs']
    bases = [b for b in json.load(open(os.path.join(WORK, 'bases.json')))['bases'] if len(b['near']) >= MIN_NEAR]
    pts = {p['id']: p for p in json.load(open(os.path.join(WORK, 'weather_points.json')))['points']}
    got = {}
    for f in glob.glob(os.path.join(WORK, 'weather', '*.json')):
        w = json.load(open(f)); got[w['id']] = w
    if not got: sys.exit('no weather points fetched yet')
    km = json.load(open(os.path.join(WORK, 'weather_points.json')))['cell_km']
    cell_of = {tuple(p['cell']): pid for pid, p in pts.items()}
    glat = np.array([w['lat'] for w in got.values()]); glon = np.array([w['lon'] for w in got.values()]); gid = list(got)
    month, year = day_months(); ndays = np.bincount(month, minlength=13)[1:] / 9
    arrays = {pid: (np.array(w['tmax'], float), np.array(w['precip'], float), np.array(w['gust'], float), w['model_elev']) for pid, w in got.items()}
    out, own = [], 0
    for b in bases:
        key = (math.floor(b['lat'] * 111.2 / km), math.floor(b['lon'] * 111.2 * math.cos(math.radians(b['lat'])) / km))
        pid = cell_of.get(key)
        if pid not in got:   # borrow the nearest fetched point
            i = int(np.argmin((glat - b['lat']) ** 2 + ((glon - b['lon']) * math.cos(math.radians(b['lat']))) ** 2)); pid = gid[i]
        else:
            own += 1
        tmax, pr, gu, zm = arrays[pid]
        h = float(np.median([(climbs[i]['foot_z'] + climbs[i]['top_z']) / 2 for i, _ in b['near']]))
        t = tmax - LAPSE / 1000 * (h - zm)
        ok = ~np.isnan(t) & ~np.isnan(pr) & ~np.isnan(gu)
        ride = ok & (t >= 11) & (pr < 1) & (gu < 50)
        per_month = np.bincount(month[ride], minlength=13)[1:] / 9          # rideable days per month, 9-year average
        index = float((MONTH_W * per_month / ndays).sum() / MONTH_W.sum())
        out.append({'node': b['node'], 'lat': b['lat'], 'lon': b['lon'], 'weather_point': pid, 'own_point': pid == cell_of.get(key),
                    'climb_height': round(h), 'model_elev': round(zm), 'ride_month': [round(x, 1) for x in per_month],
                    'ride_year': round(float(per_month.sum()), 1), 'index': round(index, 3)})
    json.dump({'lapse': LAPSE, 'summer_w': SUMMER_W, 'points_fetched': len(got), 'bases': out}, open(os.path.join(WORK, 'weather_bases.json'), 'w'))
    print(f'{len(out):,} bases with >= {MIN_NEAR} near climb scored; {own:,} with their own weather point, the rest borrowing the nearest of {len(got)} fetched')
    if check: report(out)

def report(out):
    PLACES = [('Port de Pollença', 39.905, 3.087), ('Sóller', 39.767, 2.715), ('Girona', 41.980, 2.820), ('Olot', 42.180, 2.490),
              ('Calpe', 38.645, 0.044), ('Torrox Costa', 36.728, -3.955), ('Cómpeta', 36.834, -3.973), ('Ronda', 36.742, -5.166),
              ('Granada', 37.177, -3.599), ('Jaca', 42.570, -0.549), ('Puerto de la Cruz', 28.414, -16.548)]
    print(f"\n{'place':18} {'climbs at':>9} {'weather pt':>10} {'own?':>5} {'ride/yr':>8} {'Jan':>5} {'Jul':>5} {'index':>6}")
    for name, la, lo in PLACES:
        b = min(out, key=lambda b: (b['lat'] - la) ** 2 + ((b['lon'] - lo) * math.cos(math.radians(la))) ** 2)
        print(f"{name:18} {b['climb_height']:7d} m {b['weather_point']:>10} {('yes' if b['own_point'] else 'no'):>5} {b['ride_year']:8.0f} "
              f"{b['ride_month'][0]:5.1f} {b['ride_month'][6]:5.1f} {b['index']:6.2f}")

if __name__ == '__main__':
    main('--check' in sys.argv)
