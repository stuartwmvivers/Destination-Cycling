import json, os, glob, calendar
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); C = os.path.join(ROOT, 'data', 'raw', 'meteocat'); S = os.path.join(ROOT, 'data', 'interim'); os.makedirs(S, exist_ok=True)
PAIRS = {'UE': 'begur', 'D4': 'roses', 'U2': 'lescala', 'DO': 'palamos', 'W1': 'figueres', 'XJ': 'girona', 'YB': 'olot'}
def load(st, v, y, m):
    f = os.path.join(C, f'{st}_{v}_{y}{m:02d}.json')
    if not os.path.exists(f): return None
    d = json.load(open(f))
    if not d: return {}
    vals = d.get('valors', []) if isinstance(d, dict) else []
    return {x['data'][:10]: x['valor'] for x in vals if x.get('valor') is not None and (x.get('percentatge') is None or x['percentatge'] >= 80)}
out = {}
for st, town in PAIRS.items():
    probe = json.load(open(os.path.join(C, f'{st}_probe.json')))
    gv, dv = (1512, 1515) if probe.get('1512') else ((1514, 1517) if probe.get('1514') else (None, None))
    rows = []
    for y in range(2017, 2026):
        for m in range(1, 13):
            tx, tn, pr = load(st, 1001, y, m), load(st, 1002, y, m), load(st, 1300, y, m)
            gu = load(st, gv, y, m) if gv else None
            di = load(st, dv, y, m) if dv else None
            nd = calendar.monthrange(y, m)[1]
            days = [f'{y}-{m:02d}-{d:02d}' for d in range(1, nd + 1)]
            r = {'station': st, 'place': town, 'year': y, 'month': m, 'gust_height': (10 if gv == 1512 else 2) if gv else None}
            ok_t = tx and tn and sum(1 for d in days if d in tx and d in tn) >= 0.9 * nd
            ok_p = pr and sum(1 for d in days if d in pr) >= 0.9 * nd
            ok_g = gu and sum(1 for d in days if d in gu) >= 0.9 * nd
            if ok_t:
                vx = [tx[d] for d in days if d in tx]; vn = [tn[d] for d in days if d in tn]
                r['tmax'] = round(sum(vx) / len(vx), 1); r['tmin'] = round(sum(vn) / len(vn), 1)
                r['hot'] = sum(1 for v in vx if v >= 30); r['frost'] = sum(1 for v in vn if v <= 0)
            if ok_p:
                vp = [pr[d] for d in days if d in pr]
                r['rain'] = round(sum(vp)); r['wet'] = sum(1 for v in vp if v >= 1)
            if ok_g:
                r['tram'] = sum(1 for d in days if d in gu and gu[d] * 3.6 >= 50 and di and d in di and (di[d] >= 290 or di[d] <= 40))
                r['gusty'] = sum(1 for d in days if d in gu and gu[d] * 3.6 >= 50)
            if ok_t and ok_p and ok_g:
                both = [d for d in days if d in tx and d in pr and d in gu]
                r['ride'] = sum(1 for d in both if tx[d] >= 11 and pr[d] < 1 and gu[d] * 3.6 < 50)
                r['warm'] = sum(1 for d in both if 14 <= tx[d] <= 30 and pr[d] < 1 and gu[d] * 3.6 < 50)
            rows.append(r)
    out[st] = rows
json.dump(out, open(os.path.join(S, 'stations_monthly.json'), 'w'))
for st, rows in out.items():
    print(st, PAIRS[st], 'months with temp', sum('tmax' in r for r in rows), 'rain', sum('rain' in r for r in rows), 'gust', sum('tram' in r for r in rows), 'ride', sum('ride' in r for r in rows))
