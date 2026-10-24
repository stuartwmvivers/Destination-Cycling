#!/usr/bin/env python3
"""Download the score pipeline's large inputs into the cache (DC_CACHE): OpenStreetMap extracts and
Copernicus DEM GLO-30 terrain tiles. Re-running skips complete files; partial downloads are written to
.part and renamed only when complete.

Uses urllib (which trusts the operating system's certificates) rather than requests (its own bundle).
Usage (score venv): python pipeline/score/fetch_inputs.py [--osm] [--dem]   (default: both)
Licences: OSM data ODbL (© OpenStreetMap contributors); Copernicus DEM: © DLR e.V. 2010-2014 and
© Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA.
"""
import os, shutil, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from common import OSM, DEM, OSM_EXTRACTS, DEM_URL, DEM_AREAS, dem_name

def remote_size(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=60) as r:
            return int(r.headers.get('Content-Length') or 0)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404): return None   # the DEM bucket answers 403/404 for tiles that don't exist (all sea)
        raise

def download(url, path):
    """Fetch url to path unless a complete copy exists. Returns 'got', 'had', or 'missing'."""
    size = remote_size(url)
    if size is None: return 'missing'
    if os.path.exists(path) and (not size or os.path.getsize(path) == size): return 'had'
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(path + '.part', 'wb') as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if size and os.path.getsize(path + '.part') != size: raise IOError('incomplete download')
            os.replace(path + '.part', path)
            return 'got'
        except (urllib.error.URLError, IOError, TimeoutError) as e:
            print(f'  retry {attempt + 1} for {url}: {e}', flush=True); time.sleep(10)
    raise RuntimeError(f'failed: {url}')

def main(do_osm, do_dem):
    if do_osm:
        for name, url in OSM_EXTRACTS.items():
            t = time.time(); st = download(url, os.path.join(OSM, f'{name}-latest.osm.pbf'))
            print(f'OSM {name}: {st} ({time.time() - t:.0f} s)', flush=True)
    if do_dem:
        tiles = [dem_name(la, lo) for lats, lons in DEM_AREAS for la in lats for lo in lons]
        with ThreadPoolExecutor(6) as ex:
            res = list(ex.map(lambda n: download(DEM_URL.format(n=n), os.path.join(DEM, n + '.tif')), tiles))
        print(f'DEM: {len(tiles)} tiles checked: {res.count("got")} downloaded, {res.count("had")} already had, {res.count("missing")} all-sea (none)')
        total = sum(os.path.getsize(os.path.join(DEM, f)) for f in os.listdir(DEM) if f.endswith('.tif'))
        print(f'DEM cache: {total / 1e9:.2f} GB', flush=True)

if __name__ == '__main__':
    a = sys.argv[1:]
    main('--osm' in a or not a, '--dem' in a or not a)
