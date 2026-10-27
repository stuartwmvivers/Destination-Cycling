#!/usr/bin/env python3
"""Combine the score inputs into the small file the score page reads (phase 5; spec sections 3 and 7a).

Every component is precomputed here as 0-1 per base; the page only applies the user's weights, gate and flights
mode. Inputs (all in WORK): bases.json, climbs.json, reach.npz, drive_times.npz, weather_bases.json, names.json,
network.npz (base coordinates); config/airports.json.

Bases: every base with at least one near climb (10,762 of 16,609), so the page can relax the gate (GATE_N = 3).
Components (judgement calls of 25 Oct 2026, to review with the owner at the phase 5 check-in):
  climbing   each climb is worth min(gain, GAIN_CAP) / 300 (a 300 m climb = 1), times a nearness factor of its
             foot's distance by road: 1 up to 10 km, 0.4 at 26 km, 0.1 at 60 km and beyond. Onward climbs use their
             longer distance (base -> near foot + near climb + top -> onward foot). Climbing is ABSOLUTE, not
             percentile-scaled: 0.8 x (1 - exp(-sum / CLIMB_SAT)) (a week's worth of climbs is enough: about 5 good
             nearby climbs give 0.63, 10 give 0.86) + 0.2 x the best near climb's gain x nearness, scaled 300 m -> 0
             to 1000 m -> 1. Percentile scaling (first tried) put the 95th percentile at 28 near climbs, so Pollença,
             with 4 good ones, scored 0.10.
  weather    weather_score.py's index (rideable share, October-May weighted, at the climbs' height).
  quiet      0.6 x minor-road km + 0.4 x junctions of 3+ minor roads (reach_measures.py).
  flat       minor roads under 2% average gradient.
  gravel     gravel tracks weighted by countryside quality.
  walking    0.75 x path km (mountain paths x2, waymarked bonus) + 0.25 x named peaks weighted by height.
  airport    NOT normalised: the spec's curve of drive minutes, computed in the page from the minutes stored here
             (1 up to 60 min, 0.5 at 120, then towards 0.15, never 0), so the flights mode can switch variants.
Built-up penalty (owner, 25 Oct 2026): the built-up share of usable land within 5 km of the base (WorldCover), 0 up
to BUILT_LO, rising linearly to 1 at BUILT_HI. The page multiplies the total by (1 - strength x penalty), strength
BUILT_STRENGTH by default and switchable off, so riding out through a city or resort strip every day costs points.
Reach measures are per km2 of usable land (owner, 25 Oct 2026): raw / max(land, LAND_FLOOR x disc) x disc, i.e. what
the full circle would hold if it were all like the land part, so coastal bases aren't marked down for the sea. The
floor stops a headland with a sliver of land scoring as if it were dense. The other measures (not climbing or airport) are each scaled linearly between its 5th and 95th percentile over the gate-passing bases and
clipped to 0-1, so a few extreme places (dense lowland road grids, Teide) don't squash everyone else.

Output: data/processed/score/spain.json (ODbL: derived from OpenStreetMap). Prints the validation table.
Usage (score venv): python pipeline/score/score_export.py
"""
import datetime as dt, json, math, os
import numpy as np
from scipy.spatial import cKDTree
from common import ROOT, WORK
from gate import GATE_N, REACH_KM, PLACES
from reach_measures import AREAS, Grid, RADIUS

GAIN_CAP = 1500
CLIMB_SAT = 5.0
LAND_FLOOR = 0.25
BUILT_LO, BUILT_HI, BUILT_STRENGTH = 0.10, 0.50, 0.20   # BUILT_STRENGTH must match score.js
ONWARD_MAX = 12          # onward climbs kept per base (the most valuable), to keep the file small
LO_P, HI_P = 5, 95
WEIGHTS = {'climbing': 35, 'weather': 20, 'airport': 13, 'quiet': 12, 'walking': 10, 'flat': 5, 'gravel': 5}
SEASONAL_CREDIT = 0.5    # must match score.js

def nearness(km):
    return float(np.interp(km, [10, 26, 60], [1.0, 0.4, 0.1]))

def airport_curve(minutes):
    if not math.isfinite(minutes): return 0.15
    if minutes <= 60: return 1.0
    if minutes <= 120: return 1.0 - 0.5 * (minutes - 60) / 60
    return 0.15 + 0.35 * math.exp(-(minutes - 120) / 60)

def scale(x, ref):
    lo, hi = np.percentile(ref, LO_P), np.percentile(ref, HI_P)
    return np.clip((x - lo) / (hi - lo), 0, 1), [round(float(lo), 3), round(float(hi), 3)]

def flat_coords(lat, lon):
    return np.column_stack([lat, lon * np.cos(np.radians(lat))])

def main():
    climbs = json.load(open(os.path.join(WORK, 'climbs.json')))['climbs']
    bases = [b for b in json.load(open(os.path.join(WORK, 'bases.json')))['bases'] if b['near']]
    n = len(bases)
    net = np.load(os.path.join(WORK, 'network.npz'))
    lat = net['node_lat'][[b['node'] for b in bases]].astype(float); lon = net['node_lon'][[b['node'] for b in bases]].astype(float)
    gate = np.array([len(b['near']) >= GATE_N for b in bases])

    # ---- names: bases by nearest place, climbs by the pass or peak at the top and the place near the foot
    names = json.load(open(os.path.join(WORK, 'names.json'), encoding='utf-8'))
    pl = names['places']; ptree = cKDTree(flat_coords(np.array([p['lat'] for p in pl]), np.array([p['lon'] for p in pl])))
    def place_name(la, lo, max_km):
        d, i = ptree.query(flat_coords(np.atleast_1d(la), np.atleast_1d(lo)))
        return [pl[j]['name'] if dd * 111.2 <= max_km else '' for dd, j in zip(d, i)]
    ps = names['passes']; pk = cKDTree(flat_coords(np.array([p['lat'] for p in ps]), np.array([p['lon'] for p in ps])))
    def top_name(la, lo):
        best = ''
        for j in pk.query_ball_point(flat_coords(np.array([la]), np.array([lo]))[0], 0.8 / 111.2):
            p = ps[j]
            if p['kind'] == 'pass' or not best: best = p['name']
            if p['kind'] == 'pass': break
        return best
    base_name = place_name(lat, lon, 6)
    clat = np.array([c['foot_lat'] for c in climbs]); clon = np.array([c['foot_lon'] for c in climbs])
    foot_name = place_name(clat, clon, 5)
    tops = [top_name(c['top_lat'], c['top_lon']) for c in climbs]

    # ---- climbing
    value = np.array([min(c['gain'], GAIN_CAP) / 300 for c in climbs])
    raw_sum, raw_best, onward_kept = np.zeros(n), np.zeros(n), []
    for k, b in enumerate(bases):
        near = [(i, d / 1000) for i, d in b['near']]
        onw = sorted(((i, d / 1000, via) for i, d, via in b['onward']), key=lambda t: -value[t[0]] * nearness(t[1]))[:ONWARD_MAX]
        onward_kept.append(onw)
        raw_sum[k] = sum(value[i] * nearness(d) for i, d in near) + sum(value[i] * nearness(d) for i, d, _ in onw)
        raw_best[k] = max(min(climbs[i]['gain'], GAIN_CAP) * nearness(d) for i, d in near)
    climbing = 0.8 * (1 - np.exp(-raw_sum / CLIMB_SAT)) + 0.2 * np.clip((raw_best - 300) / 700, 0, 1)
    anchors = {}

    # ---- reach measures, sampled at the bases
    R = np.load(os.path.join(WORK, 'reach.npz')); raw = {k: np.full(n, np.nan) for k in RADIUS}
    for area, box in AREAS.items():
        G = Grid(*box); r, c, ok = G.cells(lat, lon)
        for k in RADIUS: raw[k][ok] = R[f'{area}_{k}'][r[ok], c[ok]]
        for km in (5, 15, 20): raw[f'land{km}'] = raw.get(f'land{km}', np.full(n, np.nan)); raw[f'land{km}'][ok] = R[f'{area}_land{km}'][r[ok], c[ok]]
        raw['built5'] = raw.get('built5', np.full(n, np.nan)); raw['built5'][ok] = R[f'{area}_built5'][r[ok], c[ok]]
    built_share = raw['built5'] / np.maximum(raw['land5'], 1)
    built_pen = np.clip((built_share - BUILT_LO) / (BUILT_HI - BUILT_LO), 0, 1)
    dens = {}
    for k, km in RADIUS.items():
        disc = math.pi * km * km
        dens[k] = raw[k] / np.maximum(raw[f'land{km}'], LAND_FLOOR * disc) * disc
    comp = {'climbing': climbing}
    for name, parts in [('quiet', [('quiet_km', .6), ('loops', .4)]), ('flat', [('flat_km', 1)]), ('gravel', [('gravel_km', 1)]),
                        ('walking', [('walk_km', .75), ('peaks', .25)])]:
        comp[name] = 0
        for k, w in parts:
            s, anchors[k] = scale(dens[k], dens[k][gate]); comp[name] = comp[name] + w * s

    # ---- weather (may be partial while the download runs)
    wb = json.load(open(os.path.join(WORK, 'weather_bases.json')))
    wnode = {w['node']: w for w in wb['bases']}
    widx = np.array([wnode[b['node']]['index'] if b['node'] in wnode else np.nan for b in bases])
    comp['weather'], anchors['weather_index'] = scale(widx, widx[gate & ~np.isnan(widx)])

    # ---- airports: drive minutes to the nearest junction of the driving network
    dtz = np.load(os.path.join(WORK, 'drive_times.npz'))
    core = dtz['core']; dtree = cKDTree(flat_coords(dtz['lat'][core].astype(float), dtz['lon'][core].astype(float)))
    j = core[dtree.query(flat_coords(lat, lon))[1]]
    yr_min, any_min, yr_code, any_code = dtz['yr_min'][j].astype(float), dtz['any_min'][j].astype(float), dtz['yr_code'][j], dtz['any_code'][j]

    # ---- write
    r0 = lambda x: None if not math.isfinite(x) else round(float(x))
    r3 = lambda x: None if not math.isfinite(x) else round(float(x), 3)
    out_bases = {
        'lat': [round(float(x), 4) for x in lat], 'lon': [round(float(x), 4) for x in lon], 'name': base_name,
        'near': [[[i, round(d / 100)] for i, d in sorted(b['near'], key=lambda t: t[1])] for b in bases],              # distance in 0.1 km
        'onward': [[[i, round(d * 10), via] for i, d, via in sorted(o, key=lambda t: t[1])] for o in onward_kept],
        **{f'c_{k}': [r3(x) for x in v] for k, v in comp.items()},
        **{f'm_{k}': [r0(x) for x in v] for k, v in raw.items() if not k.startswith(('land', 'built'))},
        'built5': [r0(x * 100) for x in built_share], 'c_built': [r3(x) for x in built_pen],
        'land20': [r0(x / (math.pi * 400) * 100) for x in raw['land20']],      # % of the 20 km circle that is usable land
        'yr_min': [r0(x) for x in yr_min], 'yr_code': [str(x) for x in yr_code],
        'any_min': [r0(x) for x in any_min], 'any_code': [str(x) for x in any_code],
        'w_index': [r3(x) for x in widx],
        'w_ride': [wnode[b['node']]['ride_year'] if b['node'] in wnode else None for b in bases],
        'w_month': [[round(x) for x in wnode[b['node']]['ride_month']] if b['node'] in wnode else None for b in bases],
        'w_height': [wnode[b['node']]['climb_height'] if b['node'] in wnode else None for b in bases],
        'w_own': [bool(wnode[b['node']]['own_point']) if b['node'] in wnode else False for b in bases],
    }
    out_climbs = {k: [c[k] for c in climbs] for k in ['foot_lat', 'foot_lon', 'top_lat', 'top_lon', 'gain', 'length_km', 'grade']}
    out_climbs['foot_z'] = [round(c['foot_z']) for c in climbs]; out_climbs['top_z'] = [round(c['top_z']) for c in climbs]
    out_climbs['foot_name'] = foot_name; out_climbs['top_name'] = tops
    ap = json.load(open(os.path.join(ROOT, 'config', 'airports.json'), encoding='utf-8'))
    pts = json.load(open(os.path.join(WORK, 'weather_points.json')))['points']
    doc = {'generated': dt.date.today().isoformat(), 'licence': 'ODbL 1.0 (derived from OpenStreetMap)',
           'gate_n': GATE_N, 'built': {'lo': BUILT_LO, 'hi': BUILT_HI, 'strength': BUILT_STRENGTH}, 'reach_km': REACH_KM, 'weights': WEIGHTS, 'seasonal_credit': SEASONAL_CREDIT, 'anchors': anchors,
           'weather': {'points_fetched': wb['points_fetched'], 'points_total': len(pts), 'lapse': wb['lapse'], 'summer_w': wb['summer_w']},
           'airports': [{k: a[k] for k in ['code', 'name', 'lat', 'lon', 'edi', 'gla', 'confidence']} for a in ap['airports']],
           'airports_status': ap['status'],
           'places': [{'name': p[0], 'lat': p[1], 'lon': p[2], 'expect': p[3]} for p in PLACES],
           'climbs': out_climbs, 'bases': out_bases}
    os.makedirs(os.path.join(ROOT, 'data', 'processed', 'score'), exist_ok=True)
    path = os.path.join(ROOT, 'data', 'processed', 'score', 'spain.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f: json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{n:,} bases ({gate.sum():,} pass the gate), {len(climbs):,} climbs; weather from {wb["points_fetched"]} of {len(pts)} points '
          f'-> {os.path.relpath(path, ROOT)} ({os.path.getsize(path) / 1e6:.1f} MB)')
    validation(doc, comp, gate, lat, lon, yr_min, built_pen)

def validation(doc, comp, gate, lat, lon, yr_min, built_pen):
    """Default-weights rank of the named places among gate-passing bases (spec section 4)."""
    air = np.array([airport_curve(m) for m in yr_min])
    parts = {**comp, 'airport': air}
    w = doc['weights']
    total = sum(w[k] * np.nan_to_num(parts[k]) for k in w) / sum(w.values()) * 100 * (1 - BUILT_STRENGTH * built_pen)
    order = np.argsort(-np.where(gate, total, -1)); rank = np.empty(len(total), int); rank[order] = np.arange(1, len(total) + 1)
    tree = cKDTree(flat_coords(lat, lon))
    print(f"\n{'place':42} {'expect':>6} {'gate':>5} {'rank':>6} {'score':>6}  " + ' '.join(f'{k[:5]:>5}' for k in w))
    for p in doc['places']:
        d, i = tree.query(flat_coords(np.array([p['lat']]), np.array([p['lon']])))
        i = int(i[0]); far = d[0] * 111.2 > 5
        rk = f"{rank[i]:6d}" if gate[i] else '     -'
        print(f"{p['name'][:42]:42} {p['expect']:>6} {('pass' if gate[i] else 'fail'):>5} {rk} {total[i]:6.1f}  "
              + ' '.join(f'{parts[k][i]:5.2f}' for k in w) + ('  (no base within 5 km)' if far else ''))
    print(f'(rank among {gate.sum():,} gate-passing bases; weights {w}; built-up penalty at {BUILT_STRENGTH:.0%})')

if __name__ == '__main__':
    main()
