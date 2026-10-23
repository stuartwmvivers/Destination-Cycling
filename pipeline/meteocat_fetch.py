"""Download daily XEMA statistics for the 7 Costa Brava stations, 2017-2025, one call per station/variable/month.
Needs METEOCAT_API_KEY. ~3,300 calls (quota: 20,000/month on the XEMA plan). Resumable: skips files already saved.
Raw daily data stays in data/raw/ (git-ignored): Meteocat permission covers publishing MONTHLY SUMMARIES only.
"""
import json, os, sys, time, urllib.request
S = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'meteocat')
KEY = os.environ['METEOCAT_API_KEY']
PAIRS = {'UE': 'begur', 'D4': 'roses', 'U2': 'lescala', 'DO': 'palamos', 'W1': 'figueres', 'XJ': 'girona', 'YB': 'olot'}
VARS = [1001, 1002, 1300, 1512, 1515, 1514, 1517]  # TX TN PPT gust10 dir10 gust2 dir2
cache = S; os.makedirs(cache, exist_ok=True)
calls = 0
# station metadata (names, coordinates, operating status) - needed by stations_combine.py
meta_f = os.path.join(cache, 'stations.json')
if not os.path.exists(meta_f):
    req = urllib.request.Request('https://api.meteo.cat/xema/v1/estacions/metadades', headers={'X-Api-Key': KEY})
    with urllib.request.urlopen(req, timeout=60) as r: open(meta_f, 'wb').write(r.read())
def get(url):
    global calls
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={'X-Api-Key': KEY})
            with urllib.request.urlopen(req, timeout=40) as r:
                calls += 1
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            calls += 1
            if e.code == 429: time.sleep(20); continue
            if e.code in (400, 404): return None
            time.sleep(5)
        except Exception:
            time.sleep(5)
    return None
# probe which wind height each station has (one month), then fetch only those
for st in PAIRS:
    probe = os.path.join(cache, f'{st}_probe.json')
    if not os.path.exists(probe):
        have = {}
        for v in (1512, 1514):
            d = get(f'https://api.meteo.cat/xema/v1/variables/estadistics/diaris/{v}?codiEstacio={st}&any=2021&mes=06')
            have[v] = bool(d and (d.get('valors') if isinstance(d, dict) else d))
            time.sleep(0.15)
        json.dump(have, open(probe, 'w'))
    have = json.load(open(probe))
    vars_ = [1001, 1002, 1300]
    if have.get('1512'): vars_ += [1512, 1515]
    elif have.get('1514'): vars_ += [1514, 1517]
    for y in range(2017, 2026):
        for m in range(1, 13):
            for v in vars_:
                f = os.path.join(cache, f'{st}_{v}_{y}{m:02d}.json')
                if os.path.exists(f): continue
                d = get(f'https://api.meteo.cat/xema/v1/variables/estadistics/diaris/{v}?codiEstacio={st}&any={y}&mes={m:02d}')
                json.dump(d, open(f, 'w'))
                time.sleep(0.12)
    print(st, 'done', 'calls so far', calls, flush=True)
print('ALL DONE calls', calls, flush=True)
