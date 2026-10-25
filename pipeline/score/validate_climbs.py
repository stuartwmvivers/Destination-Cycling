#!/usr/bin/env python3
"""Compare found climbs (find_climbs.py) with well-known climbs.

The reference figures and coordinates below are approximate, from general knowledge, not measured: treat a
gain within about 20% as a match, and use the listing of nearby climbs to judge the rest by eye.
Usage (score venv): python pipeline/score/validate_climbs.py [climbs_test.json]
"""
import json, math, os, sys
from common import WORK

# name, approx foot (lat, lon), approx top (lat, lon), approx gain m, approx length km
KNOWN = [
    ('Sa Calobra (from the port)', (39.851, 2.806), (39.843, 2.820), 670, 9.4),
    ('Coll de Femenia (from the Ma-10 junction)', (39.869, 2.955), (39.857, 2.903), 450, 8.0),   # top corrected 25 Oct 2026 (first guess was wrong)
    ('Puig Major (from Sóller)', (39.767, 2.716), (39.795, 2.790), 800, 14.0),
    ('Coll de Sóller (from Sóller)', (39.760, 2.712), (39.725, 2.688), 450, 7.5),
    ('Coll de Rates (from Parcent)', (38.744, -0.069), (38.727, -0.091), 360, 6.5),
    ('Rocacorba', (42.081, 2.725), (42.078, 2.687), 650, 10.0),
    ('Els Àngels (from Girona)', (41.966, 2.856), (41.984, 2.910), 380, 10.0),                    # top corrected 25 Oct 2026 (first guess was wrong)
    ('Cómpeta (from Torrox Costa)', (36.735, -3.950), (36.834, -3.973), 600, 17.0),
]

def km(a, b):
    return math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * math.cos(math.radians(a[0])))

def main():
    data = json.load(open(os.path.join(WORK, sys.argv[1] if len(sys.argv) > 1 else 'climbs.json')))
    climbs = data['climbs']
    print(f"{len(climbs)} climbs; rules {data['rules']}\n")
    for name, foot, top, gain, length in KNOWN:
        near = sorted((c for c in climbs if km(top, (c['top_lat'], c['top_lon'])) < 3), key=lambda c: km(top, (c['top_lat'], c['top_lon'])) + km(foot, (c['foot_lat'], c['foot_lon'])))
        if not near:
            print(f'-- {name}: no climb found with its top within 3 km (expected ~{gain} m over ~{length} km)'); continue
        b = near[0]; match = abs(b['gain'] - gain) <= 0.2 * gain
        print(f"{'ok ' if match else '?? '} {name}: found {b['gain']:.0f} m over {b['length_km']} km at {b['grade']}% "
              f"(expected ~{gain} m over ~{length} km); foot {km(foot, (b['foot_lat'], b['foot_lon'])):.1f} km and top {km(top, (b['top_lat'], b['top_lon'])):.1f} km from the expected points")
        for c in near[1:4]:
            print(f"      also near: {c['gain']:.0f} m over {c['length_km']} km, foot {km(foot, (c['foot_lat'], c['foot_lon'])):.1f} km / top {km(top, (c['top_lat'], c['top_lon'])):.1f} km away")

if __name__ == '__main__':
    main()
