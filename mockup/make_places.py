#!/usr/bin/env python3
"""Photos and descriptions for the interface mock-up (trial, 4 Nov 2026). Not part of the site build.

Reads mockup/place_info.json (the written text and up to five chosen Wikimedia Commons files for each place) and
mockup/data/areas.json, fetches each photo's credit and licence from Commons, downloads a copy WIDTH px wide plus a
THUMB px thumbnail, and writes mockup/data/places.json (keyed by area id) and mockup/data/img/<qid>-<n>.jpg and
<qid>-<n>-t.jpg. The first photo is the one shown largest. Photos are served from
the mock-up itself, not linked from Wikimedia. Places not in the areas file are skipped with a note.
Photos are recompressed to JPEG quality QUALITY if Pillow is installed (the score venv has it), else kept as fetched.
Usage: python mockup/make_places.py
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request
try:
    from PIL import Image
except ImportError:
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__))
OUT, IMG = os.path.join(HERE, 'data'), os.path.join(HERE, 'data', 'img')
WIDTH, THUMB, QUALITY = 1280, 480, 72
UA = {'User-Agent': 'DestinationCycling-mockup/0.1 (https://github.com/stuartwmvivers/Destination-Cycling)'}
FREE = re.compile(r'^(CC0|CC BY(-SA)? [0-9.]+( [a-z]+)?|Public domain)$', re.I)

def fetch(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:
            print('  retry:', e, file=sys.stderr); time.sleep(3)
    raise RuntimeError(url)

def plain(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html or '')).strip()

def main():
    info = json.load(open(os.path.join(HERE, 'place_info.json'), encoding='utf-8'))['places']
    areas = {f"{a['name']}|{a['muni']}": a for a in json.load(open(os.path.join(OUT, 'areas.json'), encoding='utf-8'))['areas']}
    os.makedirs(IMG, exist_ok=True)
    out = {}
    for key, p in info.items():
        a = areas.get(key)
        if not a:
            print(f'{key}: not among the mock-up areas, skipped', file=sys.stderr); continue
        photos = []
        for n, title in enumerate(p['photos']):
            q = {'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': WIDTH, 'format': 'json'}
            ii = next(iter(json.loads(fetch('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(q)))['query']['pages'].values()))['imageinfo'][0]
            md = ii['extmetadata']
            lic = plain(md.get('LicenseShortName', {}).get('value'))
            if not FREE.match(lic):
                print(f'{key}: {title} licence "{lic}" not on the free list, skipped', file=sys.stderr); continue
            img, thumb = f"img/{p['qid']}-{n}.jpg", f"img/{p['qid']}-{n}-t.jpg"
            b = fetch(ii.get('thumburl') or ii['url'])
            if Image:
                im = Image.open(io.BytesIO(b)).convert('RGB'); im.thumbnail((WIDTH, WIDTH))
                for path, size in ((img, WIDTH), (thumb, THUMB)):
                    c = im.copy(); c.thumbnail((size, size))
                    buf = io.BytesIO(); c.save(buf, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
                    open(os.path.join(OUT, path), 'wb').write(buf.getvalue())
            else:
                open(os.path.join(OUT, img), 'wb').write(b); thumb = img
            photos.append({'img': img, 'thumb': thumb, 'w': im.width if Image else None, 'h': im.height if Image else None,
                           'credit': {'artist': plain(md.get('Artist', {}).get('value')) or 'Unknown', 'licence': lic,
                                      'licence_url': md.get('LicenseUrl', {}).get('value'), 'page': ii['descriptionurl']}})
            print(f"{key}: {lic}, {photos[-1]['credit']['artist']}", file=sys.stderr)
            time.sleep(0.5)
        if not photos: continue
        out[a['id']] = {'photos': photos, 'place': p['place'], 'living': p['living'], 'wiki': p.get('wiki'), 'qid': p['qid'], 'checked': p['checked']}
    json.dump({'places': out}, open(os.path.join(OUT, 'places.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(out)} places written', file=sys.stderr)

if __name__ == '__main__':
    main()
