#!/usr/bin/env python3
"""Choose the weather points for phase 4: one per CELL_KM square that contains a base passing the climbing gate,
at the mean position of those bases. Each base then uses its cell's point, with temperature adjusted to its
climbs' height (weather_score.py). Points already chosen keep their id and position, because weather_fetch.py has
saved them under that id: new cells are added after them, so extending the map costs only the new points.

Madeira and Porto Santo use smaller cells and cover every base with a near climb (common.weather_cell). Their five
earlier 25 km points (w0622, w0640, w0642, w0648, w0649) stay in the file, unused, so that ids stay unique.

Usage (score venv): python pipeline/score/weather_points.py [CELL_KM]      (default 25; prints counts for others)
"""
import json, os, sys
from common import WORK, in_madeira, weather_cell

def cells(bases, km):
    out = {}
    for b in bases:
        if len(b['near']) < (1 if in_madeira(b['lat']) else 3): continue
        key = weather_cell(b['lat'], b['lon'], km)
        out.setdefault(key, []).append(b)
    return out

def main():
    km = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0
    bases = json.load(open(os.path.join(WORK, 'bases.json')))['bases']
    for k in (15, 20, 25, 30, 40):
        n = len(cells(bases, k)); print(f'{k:3d} km cells: {n:4d} weather points, about {n / 140:.1f} days of fetching')
    path = os.path.join(WORK, 'weather_points.json')
    old = json.load(open(path)) if os.path.exists(path) else {'cell_km': km, 'points': []}
    assert old['cell_km'] == km, f"weather_points.json uses {old['cell_km']} km cells: a new size would refetch every point"
    pts = old['points']; have = {tuple(p['cell']) for p in pts}
    new = [kv for kv in cells(bases, km).items() if kv[0] not in have]
    # busiest first: points serving the most bases are fetched first, so partial results cover the main areas
    for i, ((cy, cx), bs) in enumerate(sorted(new, key=lambda kv: -len(kv[1])), len(pts)):
        pts.append({'id': f'w{i:04d}', 'lat': round(sum(b['lat'] for b in bs) / len(bs), 4), 'lon': round(sum(b['lon'] for b in bs) / len(bs), 4),
                    'cell': [cy, cx], 'bases': len(bs)})
    json.dump({'cell_km': km, 'points': pts}, open(path, 'w'))
    print(f'{len(pts)} points on {km:.0f} km cells, {len(new)} of them new -> weather_points.json')

if __name__ == '__main__':
    main()
