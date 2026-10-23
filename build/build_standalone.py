#!/usr/bin/env python3
"""Build the single-file public page (spanish-coast-climate.html) from src/dashboard.html + data.

src/dashboard.html is written against a small `dash` API (from the Claude.ai Dashboard artifact
it was first built in). src/standalone/shim.js re-implements that API in ~70 lines so the same
page runs anywhere: data are inlined as window.__CLIMATE_DATA__, d3 v7.9.0 is inlined, and the
page's own <script> blocks are moved after the shim. Output is fully offline-capable (~1 MB).

Usage: python3 build/build_standalone.py   (needs node_modules/d3 from `npm ci` in pipeline/maps or repo root)
"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(ROOT, *p)
# Always UTF-8 in, UTF-8 + LF out, so the output is byte-identical on Windows too.
read = lambda p: open(p, encoding='utf-8').read()
page = read(J('src', 'dashboard.html'))
data = {k: json.load(open(J('data', 'processed', f), encoding='utf-8')) for k, f in
        [('climate', 'climate-spain-2017-2025.json'), ('places', 'places-spain.json'),
         ('outlines', 'map-outlines-spain.json'), ('stations', 'stations-all-2017-2025.json')]}
d3_path = next(p for p in [J('node_modules', 'd3', 'dist', 'd3.min.js'), J('pipeline', 'maps', 'node_modules', 'd3', 'dist', 'd3.min.js')] if os.path.exists(p))
d3 = read(d3_path)
shim = read(J('src', 'standalone', 'shim.js'))
tokens = read(J('src', 'standalone', 'tokens.html'))
foot = ('<footer class="cb-foot">Weather data: <a href="https://open-meteo.com/">Open-Meteo</a> historical archive (ECMWF analysis, CC BY 4.0). '
        'Station readings: Costa Brava © Servei Meteorològic de Catalunya (Meteocat), used with permission; Costa del Sol, Costa Blanca and Mallorca © AEMET, Agencia Estatal de Meteorología. '
        'Coastlines: geo-maps (OpenStreetMap contributors), Natural Earth, es-atlas. Snapshot built 17 October 2026 from 2017–2025 records.</footer>')
scripts = re.findall(r'<script>.*?</script>', page, re.S)
body = page
for s in scripts: body = body.replace(s, '')
html = ('<!doctype html>\n<html lang="en-GB">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<title>Spanish Coast Climate</title>\n<meta name="description" content="Nine years of recorded weather for twenty places on the Costa Brava, Costa del Sol, Costa Blanca and Mallorca, compared with Dunning (Perthshire) and Bristol.">\n'
        + tokens + '\n</head>\n<body>\n<div id="dash-root">\n' + body + '\n' + foot + '\n</div>\n'
        + '<script>' + d3 + '</script>\n<script>window.__CLIMATE_DATA__ = ' + json.dumps(data, separators=(',', ':'), ensure_ascii=False) + ';</script>\n<script>' + shim + '</script>\n'
        + '\n'.join(scripts) + '\n</body>\n</html>\n')
open(J('spanish-coast-climate.html'), 'w', encoding='utf-8', newline='\n').write(html)
print('wrote spanish-coast-climate.html', len(html), 'bytes')
