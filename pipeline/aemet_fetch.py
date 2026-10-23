"""Download AEMET daily climatological values (6-month windows) for the 10 stations paired with
Costa del Sol / Costa Blanca / Mallorca towns. Needs AEMET_API_KEY. ~360 HTTP calls. Resumable.
Two-step API: first call returns a 'datos' URL which is then fetched without the key.
"""
import json, os, time, urllib.request
S = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ['AEMET_API_KEY']
PAIRS = {'6213X': 'nerja', '6205X': 'torrox', '6076X': 'marbella', '6058I': 'estepona', '8025': 'alicante', '8036Y': 'altea', '8050X': 'javea', 'B228': 'palma', 'B051A': 'soller', 'B760X': 'pollensa'}
C = os.path.join(os.path.dirname(S), 'data', 'raw', 'aemet'); os.makedirs(C, exist_ok=True)
def http(url, key=True):
    for a in range(6):
        try:
            req = urllib.request.Request(url, headers={'api_key': KEY} if key else {})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(65); continue
            if e.code == 404: return None
            time.sleep(10)
        except Exception:
            time.sleep(10)
    return None
for st in PAIRS:
    for y in range(2017, 2026):
        for h, (a, b) in enumerate([('01-01', '06-30'), ('07-01', '12-31')]):
            f = os.path.join(C, f'{st}_{y}_{h}.json')
            if os.path.exists(f): continue
            r = http(f'https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/fechaini/{y}-{a}T00:00:00UTC/fechafin/{y}-{b}T23:59:59UTC/estacion/{st}')
            data = []
            if r and r.get('estado') == 429:
                time.sleep(65); r = http(f'https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/fechaini/{y}-{a}T00:00:00UTC/fechafin/{y}-{b}T23:59:59UTC/estacion/{st}')
            if r and r.get('estado') == 200 and r.get('datos'):
                time.sleep(0.8)
                data = http(r['datos'], key=False) or []
            json.dump({'status': r.get('estado') if r else None, 'desc': r.get('descripcion') if r else None, 'data': data}, open(f, 'w'), ensure_ascii=False)
            time.sleep(1.5)
    print(st, 'done', flush=True)
print('ALL DONE', flush=True)
