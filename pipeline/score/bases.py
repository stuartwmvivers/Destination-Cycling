#!/usr/bin/env python3
"""Candidate bases for the score: a 5 km grid over Spain's land, each snapped onto the cycling network, with its
near climbs (foot within 26 km by road) and onward climbs (foot within 26 km of a near climb's top; spec section 8).

Grid points more than SNAP_KM from a usable road junction are dropped (sea, empty mountainsides); points that snap
to the same junction are merged. Distances are by road in legal bike directions, as in gate.py.
Output: WORK/bases.json: per base lat, lon, junction, near [[climb, metres]], onward [[climb, metres, via]].
Usage (score venv): python pipeline/score/bases.py
"""
import json, os, time
import numpy as np
from common import WORK
from graph import load, Snapper
from gate import adjacency, within, REACH_KM, GATE_N

STEP_KM, SNAP_KM = 5.0, 2.5
AREAS = [(35.9, 43.9, -9.4, 4.4), (27.6, 29.4, -18.2, -13.4)]   # mainland + Balearics, Canaries

def grid_points():
    pts = []
    for s, n, w, e in AREAS:
        dy = STEP_KM / 111.2
        for la in np.arange(s, n, dy):
            dx = STEP_KM / (111.2 * np.cos(np.radians(la)))
            for lo in np.arange(w, e, dx): pts.append((round(float(la), 5), round(float(lo), 5)))
    return pts

def main():
    t = time.time()
    d, g = load(); snap = Snapper(d, g)
    climbs = json.load(open(os.path.join(WORK, 'climbs.json')))['climbs']
    bases = {}
    for la, lo in grid_points():
        node, km = snap(la, lo)
        if km <= SNAP_KM and node not in bases: bases[node] = dict(lat=la, lon=lo, node=node, near=[], onward=[])
    print(f'{len(bases):,} bases on a {STEP_KM:.0f} km grid ({time.time() - t:.0f} s)', flush=True)
    base_nodes = set(bases)
    # near: one search per climb outwards from its foot along roads ridden towards it
    radj = adjacency(d, g, reverse=True)
    for i, c in enumerate(climbs):
        for node, dist in within(*radj, c['foot'], REACH_KM * 1000).items():
            if node in base_nodes: bases[node]['near'].append([i, round(dist)])
        if (i + 1) % 500 == 0: print(f'  near: {i + 1:,} of {len(climbs):,} climbs ({time.time() - t:.0f} s)', flush=True)
    # onward: from each climb's top, the other climbs whose foot is within reach
    fadj = adjacency(d, g)
    foot_of = {}
    for i, c in enumerate(climbs): foot_of.setdefault(c['foot'], []).append(i)
    from_top = {}
    for i, c in enumerate(climbs):
        top, _ = snap(c['top_lat'], c['top_lon'])
        reach = within(*fadj, top, REACH_KM * 1000)
        from_top[i] = {j: dd for f, ids in foot_of.items() if f in reach for j in ids if j != i for dd in [reach[f]]}
        if (i + 1) % 500 == 0: print(f'  onward: {i + 1:,} of {len(climbs):,} climbs ({time.time() - t:.0f} s)', flush=True)
    for b in bases.values():
        near = {i: dist for i, dist in b['near']}
        best = {}
        for i, dist in near.items():
            ride = dist + climbs[i]['length_km'] * 1000
            for j, dj in from_top[i].items():
                if j in near: continue
                if j not in best or ride + dj < best[j][0]: best[j] = (ride + dj, i)
        b['onward'] = [[j, round(v[0]), v[1]] for j, v in best.items()]
    out = list(bases.values())
    json.dump({'step_km': STEP_KM, 'reach_km': REACH_KM, 'gate_n': GATE_N, 'bases': out}, open(os.path.join(WORK, 'bases.json'), 'w'))
    n_pass = sum(len(b['near']) >= GATE_N for b in out)
    print(f'{len(out):,} bases; {n_pass:,} ({n_pass / len(out):.0%}) pass the gate with >= {GATE_N} near climbs ({time.time() - t:.0f} s)')

if __name__ == '__main__':
    main()
