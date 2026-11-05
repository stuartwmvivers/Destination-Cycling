#!/usr/bin/env python3
"""Leisure appeal and busyness figures for each mock-up area (trial, 5 Nov 2026). Not part of the site build.

For every area in mockup/data/areas.json, writes mockup/data/appeal.json (keyed by area id) with:
  - the Wikidata item used for the place (matched by the area's name within 8 km, or 20 km for 'near X' areas, else by
    its municipality's within 30 km; items with a Wikipedia article first, then the one with most sitelinks), its Wikipedia page views over the last 12 months in LANGS, and the number of
    different people whose geotagged Commons photos lie within 2 km of it (a box, split where it hits the API cap);
  - holiday lets and their beds, and residents, for the area's municipality in Spain (INE experimental holiday-let
    count, latest file; residents from the 2021 census via ineAtlas.data) or its parish in mainland Portugal
    (Turismo de Portugal's RNAL register; residents from Wikidata). Madeira is not in RNAL, so it gets none.
The page (mockup/app.js) turns these into ratings as percentiles among the areas; the private copy adds the price.
Downloads are cached in data/raw/appeal/ (git-ignored). Needs openpyxl (the score venv has it).
Test of method: see the signal test in the session notes (busy places beat every quiet one on views, photographers
and holiday-let beds per resident). Usage: python mockup/make_appeal.py
"""
import csv, glob, io, json, math, os, re, sys, time, unicodedata, urllib.parse, urllib.request, zipfile
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'data', 'appeal.json')
RAW = os.path.join(ROOT, 'data', 'raw', 'appeal')
UA = {'User-Agent': 'DestinationCycling-mockup/0.1 (https://github.com/stuartwmvivers/Destination-Cycling)'}
LANGS = ['en', 'es', 'ca', 'pt', 'gl', 'de', 'fr', 'nl', 'it', 'sv']
VIEWS_FROM, VIEWS_TO = '20251101', '20261031'
LETS_FILE = 'exp_viv_turistica_tabla5_MAY2026.xlsx'
SOURCES = {
    'census_dwellings.csv': 'https://www.ine.es/jaxi/files/tpx/es/csv_bdsc/59525.csv',
    LETS_FILE: f'https://ine.es/experimental/viv_turistica/{LETS_FILE}?nocab=1',
    'census_2021_municipality.zip': 'https://raw.githubusercontent.com/pablogguz/ineAtlas.data/main/data/census_2021/census_2021_municipality.zip',
}
AL = 'https://geo.turismodeportugal.pt/server/rest/services/TDP/OpenData_AL/MapServer/6/query'

def fetch(url, data=None, headers=None, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers or UA), timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            print('  retry:', e, file=sys.stderr); time.sleep(5 * (i + 1))
        except Exception as e:
            print('  retry:', e, file=sys.stderr); time.sleep(5 * (i + 1))
    raise RuntimeError(url)

def api(url, params):
    b = fetch(url + '?' + urllib.parse.urlencode(params))
    return json.loads(b) if b else None

def sparql(q):
    b = fetch('https://query.wikidata.org/sparql', data=urllib.parse.urlencode({'query': q}).encode(),
              headers={**UA, 'Accept': 'application/sparql-results+json'})
    return json.loads(b)['results']['bindings']

def raw(name):
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        os.makedirs(RAW, exist_ok=True)
        open(path, 'wb').write(fetch(SOURCES[name]))
    return path

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z]', '', s)

def km(a, b, c, d):
    return math.hypot((a - c) * 111.2, (b - d) * 111.2 * math.cos(math.radians(a)))

# ---------- Wikidata item, views, photographers ----------
def find_item(name, lat, lon, within=8):
    name = re.sub(r'^near ', '', name)
    best = None
    for part in {name, *[p.strip() for p in name.split('/')]}:
        hits = api('https://www.wikidata.org/w/api.php', {'action': 'wbsearchentities', 'search': part, 'language': 'es', 'format': 'json', 'limit': 20, 'type': 'item'})['search']
        if not hits: continue
        ents = api('https://www.wikidata.org/w/api.php', {'action': 'wbgetentities', 'ids': '|'.join(h['id'] for h in hits), 'props': 'claims|sitelinks|labels', 'languages': 'en|es|pt|ca', 'format': 'json'})['entities']
        for q, e in ents.items():
            co = e.get('claims', {}).get('P625', [{}])[0].get('mainsnak', {}).get('datavalue', {}).get('value')
            if not co or km(lat, lon, co['latitude'], co['longitude']) > within: continue
            n = len(e.get('sitelinks', {})) + 1000 * any(k[:-4] in LANGS for k in e.get('sitelinks', {}) if k.endswith('wiki'))
            if best is None or n > best['links']:   # items with a Wikipedia article first, then most sitelinks
                lab = e.get('labels', {})
                best = {'qid': q, 'links': n, 'lat': co['latitude'], 'lon': co['longitude'], 'sitelinks': e.get('sitelinks', {}),
                        'label': next((lab[l]['value'] for l in ('en', 'es', 'pt', 'ca') if l in lab), part)}
    return best

def views(sitelinks):
    total = 0
    for lang in LANGS:
        t = sitelinks.get(lang + 'wiki', {}).get('title')
        if not t: continue
        r = api(f'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/'
                + urllib.parse.quote(t.replace(' ', '_'), safe='') + f'/monthly/{VIEWS_FROM}/{VIEWS_TO}', {})
        if r: total += sum(x['views'] for x in r['items'])
        time.sleep(0.15)
    return total

def photographers(lat, lon, half_km=2.0):
    dlat = half_km / 111.2; dlon = half_km / (111.2 * math.cos(math.radians(lat)))
    cells, users, files = [(lat + dlat, lon - dlon, lat - dlat, lon + dlon)], set(), 0
    while cells:
        t, l, b, r = cells.pop()
        params = {'action': 'query', 'generator': 'geosearch', 'ggsbbox': f'{t}|{l}|{b}|{r}', 'ggsnamespace': 6, 'ggslimit': 500,
                  'prop': 'imageinfo', 'iiprop': 'user', 'format': 'json', 'formatversion': 2}
        pages, cont = [], {}
        while True:
            for i in range(5):   # the API answers busy spells with an error body rather than an HTTP error
                res = api('https://commons.wikimedia.org/w/api.php', {**params, **cont})
                if 'error' not in res: break
                print('  commons busy:', res['error'].get('code'), file=sys.stderr); time.sleep(10 * (i + 1))
            else:
                raise RuntimeError('commons kept refusing')
            pages += res.get('query', {}).get('pages', [])
            if 'continue' in res: cont = res['continue']
            else: break
        if len({p['pageid'] for p in pages}) >= 500 and (t - b) > 0.001:
            ml, mo = (t + b) / 2, (l + r) / 2
            cells += [(t, l, ml, mo), (t, mo, ml, r), (ml, l, b, mo), (ml, mo, b, r)]; continue
        files += len({p['pageid'] for p in pages})
        users |= {ii.get('user') for p in pages for ii in p.get('imageinfo', [])}
        time.sleep(0.15)
    users.discard(None)
    return len(users), files

# ---------- holiday lets ----------
def spain_tables():
    codes = {}
    for r in csv.reader(open(raw('census_dwellings.csv'), encoding='utf-8-sig'), delimiter=';'):
        if len(r) >= 4 and re.match(r'\d{5} ', r[1]):
            code, name = r[1].split(' ', 1)
            for part in [name, *name.split('/')]:
                codes.setdefault(norm(part), code)
                m = re.match(r"(.+), (el|la|los|las|l'|o|a|os|as|sa|es|s'|els|les)$", part.strip(), re.I)
                if m: codes.setdefault(norm(m.group(2) + m.group(1)), code)   # 'Garriga, la' -> 'la Garriga'
    z = zipfile.ZipFile(raw('census_2021_municipality.zip'))
    pop = {r['mun_code']: float(r['total_pop']) for r in csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding='utf-8'))}
    lets = {}
    for r in openpyxl.load_workbook(raw(LETS_FILE), read_only=True)['Distrito'].iter_rows(min_row=2, values_only=True):
        if r[0]:
            m = lets.setdefault(str(r[0])[:5], [0, 0]); m[0] += r[3] or 0; m[1] += r[6] or 0
    return codes, pop, lets

def al_stats(where):
    st = json.dumps([{'statisticType': 'count', 'onStatisticField': 'OBJECTID', 'outStatisticFieldName': 'n'},
                     {'statisticType': 'sum', 'onStatisticField': 'NrUtentes', 'outStatisticFieldName': 'beds'}])
    a = api(AL, {'where': where, 'outStatistics': st, 'f': 'json'})['features'][0]['attributes']
    return a['n'] or 0, a['beds'] or 0

def al_parish_at(lat, lon):
    """The RNAL parish code (DTMNFR) and name of the registered holiday let nearest the point, within 3 km."""
    r = api(AL, {'geometry': f'{lon},{lat}', 'geometryType': 'esriGeometryPoint', 'inSR': 4326, 'distance': 3, 'units': 'esriSRUnit_Kilometer',
                 'outFields': 'DTMNFR,Freguesia,Concelho', 'returnGeometry': 'true', 'outSR': 4326, 'f': 'json', 'resultRecordCount': 200})
    feats = r.get('features', [])
    if not feats: return None
    f = min(feats, key=lambda f: km(lat, lon, f['geometry']['y'], f['geometry']['x']))['attributes']
    return f['DTMNFR'], f['Freguesia'], f['Concelho']

def parish_pop(code):
    rows = sparql(f'SELECT ?p ?t WHERE {{ ?i wdt:P6324 "{code}" ; p:P1082 ?s . ?s ps:P1082 ?p . OPTIONAL {{ ?s pq:P585 ?t }} }}')
    rows.sort(key=lambda x: x.get('t', {}).get('value', ''))
    return int(float(rows[-1]['p']['value'])) if rows else None

def main():
    areas = json.load(open(os.path.join(HERE, 'data', 'areas.json'), encoding='utf-8'))['areas']
    out = json.load(open(OUT, encoding='utf-8'))['areas'] if os.path.exists(OUT) else {}
    codes, pop, lets = spain_tables()
    for a in areas:
        if a['id'] in out: continue
        has_wiki = lambda i: i and any(k[:-4] in LANGS for k in i['sitelinks'] if k.endswith('wiki'))
        it = find_item(a['name'], a['lat'], a['lon'])
        if not has_wiki(it) and a['name'].startswith('near '):   # 'near Mogán': the named town may be further off
            it = find_item(a['name'], a['lat'], a['lon'], 20) or it
        if not has_wiki(it) and a['muni'] != a['name']:   # e.g. a town hall item with no article: use the municipality's
            it = find_item(a['muni'], a['lat'], a['lon'], 30) or it
        row = {}
        if it:
            row.update(qid=it['qid'], item=it['label'], views=views(it['sitelinks']))
            row['photographers'], row['photos'] = photographers(it['lat'], it['lon'])
        if a['country'] == 'ES':
            code = codes.get(norm(a['muni'])) or next((codes[norm(p)] for p in a['muni'].split('/') if norm(p) in codes), None)
            if code:
                n, beds = lets.get(code, [0, 0])
                row.update(lets_unit='municipality', lets_name=a['muni'], lets=n, let_beds=beds, residents=pop.get(code))
            else:
                print(f"  no INE code for {a['muni']}", file=sys.stderr)
        elif a['lon'] > -10:   # mainland Portugal: RNAL does not cover Madeira or the Azores
            p = al_parish_at(it['lat'] if it else a['lat'], it['lon'] if it else a['lon'])
            if p:
                n, beds = al_stats(f"DTMNFR='{p[0]}'")
                row.update(lets_unit='parish', lets_name=p[1], lets=n, let_beds=beds, residents=parish_pop(p[0]))
            else:
                row.update(lets_unit='none within 3 km', lets=0, let_beds=0)
        if row.get('residents') and row.get('let_beds') is not None:
            row['beds_per_100'] = round(100 * row['let_beds'] / row['residents'], 1)
        out[a['id']] = row
        print(f"{a['name']}: {row.get('item')} ({row.get('qid')}), {row.get('views')} views, {row.get('photographers')} photographers, "
              f"{row.get('let_beds')} let beds / {row.get('residents')} in {row.get('lets_name')}", file=sys.stderr)
        json.dump({'views_period': [VIEWS_FROM, VIEWS_TO], 'langs': LANGS, 'lets_file': LETS_FILE, 'fetched': time.strftime('%Y-%m-%d'), 'areas': out},
                  open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
