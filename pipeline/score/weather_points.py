#!/usr/bin/env python3
"""Choose the weather points for phase 4: one per CELL_KM square that contains a base passing the climbing gate,
at the mean position of those bases. Each base then uses its cell's point, with temperature adjusted to its
climbs' height (weather_score.py).

Usage (score venv): python pipeline/score/weather_points.py [CELL_KM]      (default 25; prints counts for others)
"""
import json, math, os, sys
from common import WORK

def cells(bases, km):
    out = {}
    for b in bases:
        if len(b['near']) < 3: continue
        key = (math.floor(b['lat'] * 111.2 / km), math.floor(b['lon'] * 111.2 * math.cos(math.radians(b['lat'])) / km))
        out.setdefault(key, []).append(b)
    return out

def main():
    km = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0
    bases = json.load(open(os.path.join(WORK, 'bases.json')))['bases']
    for k in (15, 20, 25, 30, 40):
        n = len(cells(bases, k)); print(f'{k:3d} km cells: {n:4d} weather points, about {n / 140:.1f} days of fetching')
    pts = []
    # busiest first: points serving the most bases are fetched first, so partial results cover the main areas
    for i, ((cy, cx), bs) in enumerate(sorted(cells(bases, km).items(), key=lambda kv: -len(kv[1]))):
        pts.append({'id': f'w{i:04d}', 'lat': round(sum(b['lat'] for b in bs) / len(bs), 4), 'lon': round(sum(b['lon'] for b in bs) / len(bs), 4),
                    'cell': [cy, cx], 'bases': len(bs)})
    json.dump({'cell_km': km, 'points': pts}, open(os.path.join(WORK, 'weather_points.json'), 'w'))
    print(f'chose {len(pts)} points on {km:.0f} km cells -> weather_points.json')

if __name__ == '__main__':
    main()
