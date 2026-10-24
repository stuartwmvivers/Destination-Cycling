#!/usr/bin/env python3
"""Download Met Office MIDAS Open station files (via CEDA) for the UK baselines.

No single station near Dunning or Bristol has temperature, rain and wind for 2017-2025, so each
baseline is a pair: one synoptic station for temperature and gusts, one rain gauge (see STATIONS).
Files go to the git-ignored cache data/raw/midas/<dataset>/; existing files are skipped.

Needs CEDA_ACCESS_TOKEN (from the CEDA account's access-token page; tokens are short-lived) in the
environment or in the git-ignored .env. Directory listings are public; downloads need the token.

Usage: python3 pipeline/midas_fetch.py            (then midas_aggregate.py, stations_combine.py)
       python3 pipeline/midas_fetch.py --list     (show what would be downloaded; no token needed)
Licence: Open Government Licence v3; cite the dataset version (HANDOVER 6).
"""
import os, re, sys, time, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://dap.ceda.ac.uk/badc/ukmo-midas-open/data'
VERSION = 'dataset-version-202607'
YEARS = range(2017, 2026)
# place -> {role: (county folder, station folder)}; 'tw' = temperature + wind, 'rain' = rain gauge
STATIONS = {
    'dunning': {'tw': ('perthshire-in-tayside-region', '00212_strathallan-airfield'),
                'rain': ('perthshire-in-tayside-region', '55762_kinkell-bridge-no-2')},
    'bristol': {'tw': ('avon', '62122_almondsbury'),
                'rain': ('avon', '09621_clifton-oakfield-road')},
}
DATASETS = {'tw': ['uk-daily-temperature-obs', 'uk-mean-wind-obs'], 'rain': ['uk-daily-rain-obs']}

def token():
    t = os.environ.get('CEDA_ACCESS_TOKEN')
    if not t and os.path.exists(os.path.join(ROOT, '.env')):
        for line in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
            k, _, v = line.strip().partition('=')
            if k.strip() == 'CEDA_ACCESS_TOKEN': t = v.strip().strip('"\'')
    return t

def get(url, tok=None):
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {tok}'} if tok else {})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403): sys.exit(f'HTTP {e.code} for {url}: the CEDA token is missing, wrong or expired')
            if e.code == 404: return None
            time.sleep(5)
        except urllib.error.URLError:
            time.sleep(5)
    raise RuntimeError(f'failed to fetch {url}')

def files_for(ds, county, station):
    """The station's quality-controlled yearly CSVs for YEARS (each has the station's position and height in its
    header) plus its capability file, from the public directory listing."""
    url = f'{BASE}/{ds}/{VERSION}/{county}/{station}/'
    names = set(re.findall(r'href="([^"/]+\.csv)"', (get(url + 'qc-version-1/') or b'').decode()))
    years = sorted(n for n in names if (m := re.search(r'_(\d{4})\.csv$', n)) and int(m.group(1)) in YEARS)
    meta = re.findall(r'href="([^"/]+_capability\.csv)"', (get(url) or b'').decode())
    return [url + 'qc-version-1/' + n for n in years] + [url + m for m in meta]

def main(list_only):
    tok = None if list_only else token()
    if not list_only and not tok: sys.exit('Set CEDA_ACCESS_TOKEN in the environment or in .env')
    got = skipped = 0
    for place, roles in STATIONS.items():
        for role, (county, station) in roles.items():
            for ds in DATASETS[role]:
                urls = files_for(ds, county, station)
                print(f'{place:8} {role:4} {ds:26} {station:30} {len(urls)} files')
                if list_only: continue
                out = os.path.join(ROOT, 'data', 'raw', 'midas', ds)
                os.makedirs(out, exist_ok=True)
                for u in urls:
                    f = os.path.join(out, u.rsplit('/', 1)[1])
                    if os.path.exists(f): skipped += 1; continue
                    body = get(u, tok)
                    if body is None or not body.lstrip().startswith(b'Conventions,G,BADC-CSV'): sys.exit(f'unexpected response for {u} (not a BADC-CSV file): check the token')
                    open(f, 'wb').write(body); got += 1
    if not list_only: print(f'downloaded {got}, already had {skipped}')

if __name__ == '__main__':
    main('--list' in sys.argv)
