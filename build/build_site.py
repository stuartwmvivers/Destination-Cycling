#!/usr/bin/env python3
"""Build the static site into _site/ from config/, data/processed/ and site-src/.

  config/places.json, config/regions.json      what to build
  data/processed/climate/<country>.json         monthly modelled rows (HANDOVER 4.2)
  data/processed/stations/<country>.json        monthly station rows (HANDOVER 5.3)
  site-src/pages, css, js                       page templates, styles, scripts

Output (git-ignored; deployed by GitHub Actions):
  _site/index.html                    landing page
  _site/<region>/index.html           one dashboard per region, all from site-src/pages/region.html
  _site/data/regions/<region>.json    that region's places (plus UK baselines), climate and stations, columnar
  _site/data/summary.json             every place: 9-year monthly and whole-year averages
  _site/css, js, vendor               shared files

No numbers are computed here beyond what the page itself computes; the rounding of averages in
summary.json matches the dashboard's (JavaScript Math.round, halves up).

Usage: python3 build/build_site.py   (needs node_modules/d3 from `npm ci`)
"""
import glob, json, math, os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(ROOT, *p)
OUT = J('_site')
read = lambda p: open(p, encoding='utf-8').read()
load = lambda p: json.load(open(p, encoding='utf-8'))
esc = lambda s: s.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
MEASURES = ['tmax', 'tmin', 'rain', 'wet', 'ride', 'warm', 'hot', 'frost', 'tram']
STATION_INFO = ['source', 'station', 'station_name', 'distance_km', 'elevation_m', 'gust_height_m']
D3 = '7.9.0'
LEAFLET = '1.9.4'

def write(rel, text):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8', newline='\n').write(text)
    return len(text.encode('utf-8'))

def jsround(x, nd=1):
    f = 10 ** nd
    return math.floor(x * f + 0.5) / f

def rows_by_place(sub):
    out = {}
    for f in sorted(glob.glob(J('data', 'processed', sub, '*.json'))):
        for r in load(f): out.setdefault(r['place'], []).append(r)
    return out

places = load(J('config', 'places.json'))
regions = load(J('config', 'regions.json'))
climate = rows_by_place('climate')
stations = rows_by_place('stations')
years = sorted({r['year'] for rs in climate.values() for r in rs})
months = [(y, m) for y in years for m in range(1, 13)]

def columns(rows):
    """One array per measure over the full year-month grid; null where a month is absent."""
    by = {(r['year'], r['month']): r for r in rows}
    return {m: [by[k][m] if k in by else None for k in months] for m in MEASURES}

for p in places:
    got = {(r['year'], r['month']) for r in climate.get(p['place'], [])}
    assert got == set(months), f"{p['place']}: modelled data must cover every month {years[0]}-{years[-1]}"

# ---------- data files ----------
def clean(path):
    """Delete the previous build. Sync tools (OneDrive here) briefly lock folders, so retry rather than fail."""
    import stat, time
    assert os.path.basename(path) == '_site'
    for attempt in range(10):
        if not os.path.exists(path): return
        try:
            shutil.rmtree(path, onexc=lambda f, p, e: (os.chmod(p, stat.S_IWRITE), f(p)))
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f'could not delete {path}; close anything using it and retry')
clean(OUT)
sizes = {}
for reg in regions:
    members = [p for p in places if p['country'] in reg['countries'] or p['place'] in reg['baselines']]
    st = {}
    for p in members:
        if p['place'] in stations:
            rs = stations[p['place']]
            info = {k: rs[0][k] for k in STATION_INFO}
            assert all({k: r[k] for k in STATION_INFO} == info for r in rs), f"{p['place']}: station details vary"
            st[p['place']] = {**info, 'series': columns(rs)}
    data = {'id': reg['id'], 'name': reg['name'], 'years': years, 'places': members,
            'climate': {p['place']: columns(climate[p['place']]) for p in members}, 'stations': st}
    rel = f"data/regions/{reg['id']}.json"
    sizes[rel] = write(rel, json.dumps(data, ensure_ascii=False, separators=(',', ':')))

def averages(rows):
    """9-year averages by month ('1'..'12') and whole year, as the dashboard's 'periods' calc makes them."""
    out = {}
    for m in MEASURES:
        r = 0 if m == 'rain' else 1
        by_month = [jsround(sum(x[m] for x in rows if x['month'] == mo) / len(years), r) for mo in range(1, 13)]
        per_year = [sum(x[m] for x in rows if x['year'] == y) for y in years]
        if m in ('tmax', 'tmin'): per_year = [jsround(v / 12, 1) for v in per_year]
        out[m] = by_month + [jsround(sum(per_year) / len(years), r)]
    return out

summary = {'years': years, 'periods': [str(i) for i in range(1, 13)] + ['year'], 'places': [
    {**{k: p[k] for k in ['place', 'name', 'country', 'region', 'lat', 'lon', 'elevation_m'] if k in p},
     'baseline': bool(p.get('baseline')),
     'regions': [r['id'] for r in regions if p['country'] in r['countries'] or p['place'] in r['baselines']],
     'avg': averages(climate[p['place']])} for p in places]}
sizes['data/summary.json'] = write('data/summary.json', json.dumps(summary, ensure_ascii=False, separators=(',', ':')))

# ---------- shared files ----------
for sub in ['css', 'js']:
    shutil.copytree(J('site-src', sub), os.path.join(OUT, sub))
d3 = next(p for p in [J('node_modules', 'd3', 'dist', 'd3.min.js')] if os.path.exists(p))
assert load(J('node_modules', 'd3', 'package.json'))['version'] == D3, 'd3 version changed: update D3 and test'
os.makedirs(os.path.join(OUT, 'vendor'))
shutil.copy(d3, os.path.join(OUT, 'vendor', f'd3-{D3}.min.js'))
assert load(J('node_modules', 'leaflet', 'package.json'))['version'] == LEAFLET, 'Leaflet version changed: update LEAFLET and test'
lf = os.path.join(OUT, 'vendor', f'leaflet-{LEAFLET}')
os.makedirs(lf)
for f in ['leaflet.js', 'leaflet.css']: shutil.copy(J('node_modules', 'leaflet', 'dist', f), lf)
shutil.copytree(J('node_modules', 'leaflet', 'dist', 'images'), os.path.join(lf, 'images'))

def page(rel, title, description, css, body, foot, scripts=()):
    root = '../' * rel.count('/')
    html = ('<!doctype html>\n<html lang="en-GB">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{esc(title)}</title>\n<meta name="description" content="{esc(description)}">\n'
            + ''.join(f'<link rel="stylesheet" href="{root}{c if "/" in c else f"css/{c}.css"}">\n' for c in ['tokens'] + css)
            + '</head>\n<body>\n<div id="dash-root">\n' + body + f'\n<footer class="cb-foot">{foot}</footer>\n</div>\n'
            + ''.join(s.replace('{{ROOT}}', root) + '\n' for s in scripts)
            + '</body>\n</html>\n')
    sizes[rel] = write(rel, html)

# ---------- region pages ----------
region_body = read(J('site-src', 'pages', 'region.html'))
for reg in regions:
    page(f"{reg['id']}/index.html", reg['title'], reg['description'], [f'vendor/leaflet-{LEAFLET}/leaflet.css', 'dashboard'], region_body, reg['credits'], [
        f'<script src="{{{{ROOT}}}}vendor/d3-{D3}.min.js"></script>',
        f'<script src="{{{{ROOT}}}}vendor/leaflet-{LEAFLET}/leaflet.js"></script>',
        '<script>window.DC_PAGE = ' + json.dumps({'region': reg['id'], 'root': '{{ROOT}}'}) + ';</script>',
        '<script src="{{ROOT}}js/dash-shim.js"></script>',
        '<script src="{{ROOT}}js/periods.js"></script>',
        '<script src="{{ROOT}}js/dashboard.js"></script>'])

# ---------- landing page ----------
ride = {p['place']: p['avg']['ride'][12] for p in summary['places']}
ranked = sorted(places, key=lambda p: -ride[p['place']])
top = max(ride.values())
bars = '\n'.join(
    f'      <li class="{"lp-uk" if p.get("baseline") else ""}"><span class="lp-name">{esc(p["name"])} <span class="lp-reg">· {esc(p["region"])}</span></span>'
    f'<span class="lp-track"><span class="lp-bar" style="width:{ride[p["place"]] / top * 100:.1f}%"></span></span>'
    f'<span class="lp-val">{ride[p["place"]]:.0f}</span></li>' for p in ranked)
spain = next(r for r in regions if r['id'] == 'spain-coast')
index_body = (read(J('site-src', 'pages', 'index.html'))
              .replace('{{RIDE_BARS}}', bars)
              .replace('{{SPAIN_COUNT}}', str(sum(p['country'] in spain['countries'] for p in places)))
              .replace('{{STATION_COUNT}}', str(sum(p['place'] in stations for p in places if p['country'] in spain['countries']))))
page('index.html', 'Destination Cycling',
     'Comparing places in Europe as year-round road-cycling bases, starting with nine years of weather on the Spanish coast.',
     ['landing'], index_body,
     'Weather data: <a href="https://open-meteo.com/">Open-Meteo</a> historical archive (ECMWF analysis, CC BY 4.0). '
     'Station readings on the Spain dashboard: © Servei Meteorològic de Catalunya (Meteocat), used with permission; © AEMET, Agencia Estatal de Meteorología. '
     'Source and method: <a href="https://github.com/stuartwmvivers/Destination-Cycling">GitHub</a>.')

# ---------- redirects: old URLs that must keep working ----------
for old, new in [('spanish-coast-climate.html', 'spain-coast/')]:
    sizes[old] = write(old, '<!doctype html>\n<html lang="en-GB">\n<head>\n<meta charset="utf-8">\n'
                       f'<title>Moved</title>\n<link rel="canonical" href="{new}">\n<meta http-equiv="refresh" content="0; url={new}">\n'
                       f'<script>location.replace({json.dumps(new)} + location.hash);</script>\n</head>\n'
                       f'<body><p>This page has moved to <a href="{new}">{new}</a>.</p></body>\n</html>\n')

for rel, n in sorted(sizes.items()): print(f'  {rel:40} {n / 1024:7.1f} KB')
print('built', OUT)
