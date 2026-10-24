#!/usr/bin/env python3
"""Sanity-check the road network: riding distances between well-known pairs of places should be close to
the usual road distance (approximate figures from general knowledge; a coarse check, ±25%).

Usage (score venv): python pipeline/score/check_network.py
"""
from graph import load, Snapper

# (from, lat, lon), (to, lat, lon), approximate road km by bike-legal roads
PAIRS = [
    (('Port de Pollença', 39.905, 3.087), ('Pollença', 39.877, 3.016), 7),
    (('Pollença', 39.877, 3.016), ('Alcúdia', 39.853, 3.121), 10),
    (('Palma', 39.570, 2.650), ('Sóller', 39.766, 2.715), 30),        # over the Coll de Sóller (the tunnel bans bikes)
    (('Girona', 41.980, 2.820), ('Banyoles', 42.117, 2.766), 19),
    (('Calpe', 38.645, 0.044), ('Altea', 38.599, -0.051), 11),
    (('Nerja', 36.746, -3.876), ('Frigiliana', 36.791, -3.896), 7),
    (('Puerto de la Cruz', 28.414, -16.548), ('La Orotava', 28.390, -16.523), 6),
]

def main():
    d, g = load()
    snap = Snapper(d, g)
    print(f'{g.vcount():,} junctions, {g.ecount():,} directed edges; {len(snap.core):,} junctions ({len(snap.core) / g.vcount():.0%}) in the usable core')
    bad = 0
    for (a, la1, lo1), (b, la2, lo2), km in PAIRS:
        (ia, da), (ib, db) = snap(la1, lo1), snap(la2, lo2)
        dist = g.distances(source=ia, target=ib, weights='w')[0][0] / 1000
        ok = abs(dist - km) <= 0.25 * km
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {a} -> {b}: {dist:.1f} km by network (expected about {km}); snapped within {da:.2f} / {db:.2f} km")
    print('all within 25%' if not bad else f'{bad} pairs outside 25%')

if __name__ == '__main__':
    main()
