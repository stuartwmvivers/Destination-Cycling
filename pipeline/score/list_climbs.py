#!/usr/bin/env python3
"""List found climbs (find_climbs.py), optionally only those whose foot is within R km of a point.
Usage (score venv): python pipeline/score/list_climbs.py [climbs.json] [LAT LON RADIUS_KM]
"""
import json, math, os, sys
from common import WORK

def main():
    a = sys.argv[1:]
    name = a.pop(0) if a and a[0].endswith('.json') else 'climbs.json'
    climbs = json.load(open(os.path.join(WORK, name)))['climbs']
    if len(a) >= 3:
        la, lo, r = map(float, a[:3])
        dist = lambda c: math.hypot((c['foot_lat'] - la) * 111.2, (c['foot_lon'] - lo) * 111.2 * math.cos(math.radians(la)))
        climbs = sorted((c for c in climbs if dist(c) <= r), key=dist)
    for c in climbs:
        print(f"foot {c['foot_lat']:.4f},{c['foot_lon']:.4f} ({c['foot_z']:.0f} m) -> top {c['top_lat']:.4f},{c['top_lon']:.4f} ({c['top_z']:.0f} m): "
              f"{c['gain']:.0f} m over {c['length_km']} km at {c['grade']}%")
    print(f'{len(climbs)} climbs')

if __name__ == '__main__':
    main()
