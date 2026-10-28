#!/usr/bin/env python3
"""Data for the interface mock-up (docs/interface-plan.md, DC-27). Not part of the site build.

Areas: bases one per SPREAD_KM (as the score page's "one per area" list): the best AREAS under the agreed default settings,
the best AREAS counting summer-only flights, and the best REGION_MIN on the Balearics and the Canaries.
For each: its score components (so the mock-up can re-rank live), place, setting, airports, near climbs, and the year's
weather at the base itself:
- the high at the base's own height: the weather point's daily high (2017-2025), moved from the model's height
  to the base's height (Copernicus DEM) at LAPSE degrees per km, as weather_score.py does for the climbs;
- dry days (< 1 mm); "sit-out" days (high >= 18 C and dry); rideable days as the score's (at the climbs' height).
Writes mockup/data/areas.json and, if the private join exists, mockup/data/prices.json (private: mockup/data is git-ignored).
Usage (score venv, DC_CACHE set): python mockup/make_data.py
"""
import datetime as dt, json, math, os, sys
import numpy as np, rasterio
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pipeline', 'score'))
from common import ROOT, WORK, DEM, dem_name
from price_shortlist import airport_curve, PROVINCES

AREAS, REGION_MIN, SPREAD_KM, LAPSE = 80, 8, 15, 6.5
REGIONS = {'balearics': lambda lat, lon: 38.5 < lat < 40.3 and lon > 1.1,   # as app.js's WHERE filters
           'canaries': lambda lat, lon: lat < 30}
OUT = os.path.join(ROOT, 'mockup', 'data')

def setting(built):
    return 'Countryside' if built < 4 else 'Village' if built < 10 else 'Small town' if built < 20 else 'Town' if built < 35 else 'City edge'

def elevation(lat, lon):
    f = os.path.join(DEM, dem_name(math.floor(lat), math.floor(lon)) + '.tif')
    if not os.path.exists(f): return None
    with rasterio.open(f) as r:
        v = next(r.sample([(lon, lat)]))[0]
    return None if v < -100 else float(v)

def main():
    d = json.load(open(os.path.join(ROOT, 'data', 'processed', 'score', 'spain.json'), encoding='utf-8'))
    B, W, C = d['bases'], d['weights'], d['climbs']; N = len(B['lat'])
    # spain.json lists bases as score_export.py does (bases.json with a near climb, in order); weather is keyed by network node
    nodes = [b['node'] for b in json.load(open(os.path.join(WORK, 'bases.json')))['bases'] if b['near']]
    assert len(nodes) == N, 'bases.json out of step with spain.json'
    wnode = {w['node']: w for w in json.load(open(os.path.join(WORK, 'weather_bases.json')))['bases']}
    wb = [wnode[n] for n in nodes]
    mu = json.load(open(os.path.join(WORK, 'municipalities.json'), encoding='utf-8'))
    def total(i, seasonal):
        ap = airport_curve(B['yr_min'][i])
        if seasonal: ap = max(ap, d['seasonal_credit'] * airport_curve(B['any_min'][i]))
        return (sum(W[k] * ((B['c_' + k][i] or 0) if k != 'airport' else ap) for k in W) / sum(W.values()) * 100
                * (1 - d['built']['strength'] * (B['c_built'][i] or 0)))
    gated = [i for i in range(N) if len(B['near'][i]) >= d['gate_n']]
    km = lambda i, j: math.hypot(B['lat'][i] - B['lat'][j], (B['lon'][i] - B['lon'][j]) * math.cos(math.radians(B['lat'][i]))) * 111.2
    def spread(pool, n, seasonal, taken=()):
        """The best n of pool under one setting, one per SPREAD_KM; skips any within SPREAD_KM of taken."""
        out = []
        for i in sorted(pool, key=lambda i: -total(i, seasonal)):
            if all(km(i, j) > SPREAD_KM for j in out): out.append(i)
            if len(out) >= n: break
        return [i for i in out if all(km(i, j) > SPREAD_KM for j in taken)]
    # the page re-ranks only these areas, so pick them under more than one setting (owner, 28 October 2026: no Balearic
    # area made the default 80, as their airports have only summer flights): the best AREAS with year-round flights,
    # the best AREAS counting summer-only routes too, and the best REGION_MIN on each island group
    top = spread(gated, AREAS, False)
    top += spread(gated, AREAS, True, top)
    for region in REGIONS.values():
        top += spread([i for i in gated if region(B['lat'][i], B['lon'][i])], REGION_MIN, True, top)
    top.sort(key=lambda i: -total(i, False))

    d0 = dt.date(2017, 1, 1); month = np.array([(d0 + dt.timedelta(days=k)).month for k in range(3287)])
    years = 9; cache = {}
    def point(pid):
        if pid not in cache:
            w = json.load(open(os.path.join(WORK, 'weather', pid + '.json')))
            cache[pid] = (np.array(w['tmax'], float), np.array(w['precip'], float), w['model_elev'])
        return cache[pid]

    airports = {a['code']: a for a in d['airports']}
    areas = []
    for rank, i in enumerate(top, 1):
        z = elevation(B['lat'][i], B['lon'][i])
        tmax, pr, zm = point(wb[i]['weather_point'])
        t = tmax - LAPSE / 1000 * ((z if z is not None else wb[i]['climb_height']) - zm)
        ok = ~np.isnan(t) & ~np.isnan(pr)
        high = [round(float(np.nanmean(t[month == m])), 1) for m in range(1, 13)]
        dry = [round(float(np.bincount(month[ok & (pr < 1)], minlength=13)[m] / years), 1) for m in range(1, 13)]
        sit = [round(float(np.bincount(month[ok & (pr < 1) & (t >= 18)], minlength=13)[m] / years), 1) for m in range(1, 13)]
        climbs = []
        for c, road in sorted(B['near'][i], key=lambda x: -C['gain'][x[0]])[:10]:
            climbs.append({'name': C['top_name'][c] or C['foot_name'][c] or 'Unnamed climb', 'from': C['foot_name'][c],
                           'gain': C['gain'][c], 'km': C['length_km'][c], 'grade': C['grade'][c], 'top_z': C['top_z'][c],
                           'away_km': road / 10, 'foot': [C['foot_lat'][c], C['foot_lon'][c]], 'top': [C['top_lat'][c], C['top_lon'][c]]})
        m = mu['base_muni'][i]; mm = mu['munis'][m] if m >= 0 else None
        ap = lambda code: {'code': code, 'name': airports[code]['name'], 'edi': airports[code].get('edi'), 'gla': airports[code].get('gla')} if code else None
        areas.append({
            'id': f'a{i}', 'base': i, 'default_rank': rank, 'name': B['name'][i], 'lat': B['lat'][i], 'lon': B['lon'][i],
            'muni': mm['name'] if mm else None, 'province': PROVINCES.get(mm['ine'][:2], '') if mm else '',
            'elev': None if z is None else round(z), 'built5': B['built5'][i], 'setting': setting(B['built5'][i] or 0),
            'c': {k: B['c_' + k][i] for k in ['climbing', 'weather', 'quiet', 'walking', 'flat', 'gravel', 'built']},
            'near_n': len(B['near'][i]),
            'yr': {'min': B['yr_min'][i], **(ap(B['yr_code'][i]) or {})} if B['yr_code'][i] else None,
            'any': {'min': B['any_min'][i], **(ap(B['any_code'][i]) or {})} if B['any_code'][i] else None,
            'm': {k: B['m_' + k][i] for k in ['quiet_km', 'loops', 'flat_km', 'gravel_km', 'walk_km', 'peaks']},
            'ride': B['w_month'][i], 'ride_year': B['w_ride'][i], 'own_weather': B['w_own'][i],
            'high': high, 'dry': dry, 'sit': sit, 'climbs': climbs,
        })
    os.makedirs(OUT, exist_ok=True)
    meta = {'generated': d['generated'], 'weights': W, 'seasonal_credit': d['seasonal_credit'], 'built': d['built'], 'gate_n': d['gate_n'],
            'weather': d['weather'], 'airports_status': d['airports_status'],
            'airports': {a['code']: {'name': a['name'], 'edi': a.get('edi'), 'gla': a.get('gla')} for a in d['airports']}}
    json.dump({'meta': meta, 'areas': areas}, open(os.path.join(OUT, 'areas.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{len(areas)} areas -> mockup/data/areas.json ({os.path.getsize(os.path.join(OUT, "areas.json")) // 1024} KB)')

    # every base, for the Explore map: what the page needs to score and describe it, in columns, rounded
    codes = sorted({c for c in B['yr_code'] + B['any_code'] if c and c != 'None'})
    names = sorted(set(B['name'])); name_ix = {n: k for k, n in enumerate(names)}
    r2 = lambda x: None if x is None else round(x, 2)
    grid = {'codes': codes, 'names': names,
            'munis': [[m['name'], PROVINCES.get(m['ine'][:2], '')] for m in mu['munis']], 'mu': mu['base_muni'],
            'lat': B['lat'], 'lon': B['lon'], 'nm': [name_ix[n] for n in B['name']], 'n': [len(x) for x in B['near']],
            **{k: [r2(x) for x in B['c_' + k]] for k in ['climbing', 'weather', 'quiet', 'walking', 'flat', 'gravel', 'built']},
            'ym': B['yr_min'], 'yc': [codes.index(c) if c in codes else -1 for c in B['yr_code']],
            'am': B['any_min'], 'ac': [codes.index(c) if c in codes else -1 for c in B['any_code']], 'wr': [None if x is None else round(x) for x in B['w_ride']],
            'area': {a['id']: a['base'] for a in areas}}
    json.dump(grid, open(os.path.join(OUT, 'grid.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{N:,} bases -> mockup/data/grid.json ({os.path.getsize(os.path.join(OUT, "grid.json")) // 1024} KB)')

    sp = os.path.join(ROOT, 'data', 'private', 'score_prices.json')
    if os.path.exists(sp):   # private: never commit (mockup/data is git-ignored)
        p = json.load(open(sp, encoding='utf-8')); out = {}
        for a in areas:
            k = p['base_muni'][a['base']]
            if k is not None and k >= 0: out[a['id']] = p['munis'][k]
        json.dump({'source': p.get('source'), 'prices': out, 'grid_eur': [p['munis'][k]['eur_m2'] if k is not None and k >= 0 else None for k in p['base_muni']]},
                  open(os.path.join(OUT, 'prices.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print(f'{len(out)} of {len(areas)} areas priced -> mockup/data/prices.json (private)')
    for a in areas[:12]:
        print(f"{a['default_rank']:>3} {a['name']:<24} {a['setting']:<11} {a['elev']} m  Jan high {a['high'][0]}  Jan sit-out {a['sit'][0]}  {a['yr']['code'] if a['yr'] else '-'} {a['yr']['min'] if a['yr'] else ''}")

if __name__ == '__main__':
    main()
