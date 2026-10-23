import json, os, calendar
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); C = os.path.join(ROOT, 'data', 'raw', 'aemet'); S = os.path.join(ROOT, 'data', 'interim'); os.makedirs(S, exist_ok=True)
PAIRS = {'6213X': 'nerja', '6205X': 'torrox', '6076X': 'marbella', '6058I': 'estepona', '8025': 'alicante', '8036Y': 'altea', '8050X': 'javea', 'B228': 'palma', 'B051A': 'soller', 'B760X': 'pollensa'}
def num(v):
    if v is None: return None
    v = str(v).strip()
    if v == 'Ip': return 0.05
    if v in ('Acum', 'Varias', ''): return None
    try: return float(v.replace(',', '.'))
    except ValueError: return None
inv = {s['indicativo']: s for s in json.load(open(os.path.join(ROOT, 'data', 'reference', 'aemet-station-inventory.json'), encoding='latin-1'))}
out = {}
for st, town in PAIRS.items():
    days = {}
    for y in range(2017, 2026):
        for h in (0, 1):
            f = os.path.join(C, f'{st}_{y}_{h}.json')
            if not os.path.exists(f): continue
            for d in json.load(open(f)).get('data') or []:
                days[d['fecha']] = {'tx': num(d.get('tmax')), 'tn': num(d.get('tmin')), 'p': num(d.get('prec')), 'g': num(d.get('racha')), 'dir': num(d.get('dir'))}
    has_wind = sum(1 for v in days.values() if v['g'] is not None) > 1000
    rows = []
    for y in range(2017, 2026):
        for m in range(1, 13):
            nd = calendar.monthrange(y, m)[1]
            ds = [days.get(f'{y}-{m:02d}-{d:02d}') for d in range(1, nd + 1)]
            ds = [d for d in ds if d]
            r = {'station': st, 'place': town, 'year': y, 'month': m}
            T = [d for d in ds if d['tx'] is not None and d['tn'] is not None]
            Pp = [d for d in ds if d['p'] is not None]
            G = [d for d in ds if d['g'] is not None]
            if len(T) >= 0.9 * nd:
                r['tmax'] = round(sum(d['tx'] for d in T) / len(T), 1); r['tmin'] = round(sum(d['tn'] for d in T) / len(T), 1)
                r['hot'] = sum(1 for d in T if d['tx'] >= 30); r['frost'] = sum(1 for d in T if d['tn'] <= 0)
            if len(Pp) >= 0.9 * nd:
                r['rain'] = round(sum(d['p'] for d in Pp)); r['wet'] = sum(1 for d in Pp if d['p'] >= 1)
            if has_wind and len(G) >= 0.9 * nd:
                r['tram'] = sum(1 for d in G if d['g'] * 3.6 >= 50 and d['dir'] is not None and d['dir'] != 99 and (d['dir'] * 10 >= 290 or d['dir'] * 10 <= 40))
            if 'tmax' in r and 'rain' in r and 'tram' in r:
                B = [d for d in ds if d['tx'] is not None and d['p'] is not None and d['g'] is not None]
                r['ride'] = sum(1 for d in B if d['tx'] >= 11 and d['p'] < 1 and d['g'] * 3.6 < 50)
                r['warm'] = sum(1 for d in B if 14 <= d['tx'] <= 30 and d['p'] < 1 and d['g'] * 3.6 < 50)
            rows.append(r)
    out[st] = {'name': inv[st]['nombre'], 'elev': float(inv[st]['altitud']), 'wind': has_wind, 'rows': rows}
json.dump(out, open(os.path.join(S, 'aemet_monthly.json'), 'w'), ensure_ascii=False)
for st, o in out.items():
    rs = o['rows']; print(st, PAIRS[st], o['name'], 'wind' if o['wind'] else 'no-wind', 'temp', sum('tmax' in r for r in rs), 'rain', sum('rain' in r for r in rs), 'ride', sum('ride' in r for r in rs))
