#!/usr/bin/env python3
"""Climbing gate (spec section 8): a base passes with at least GATE_N NEAR climbs (find_climbs.py).

Within reach (owner, 24-25 Oct 2026):
  - near climbs: the foot is within REACH_KM by road (legal bike directions) of the base;
  - onward climbs: the foot is within REACH_KM by road of the TOP of a near climb, i.e. reached by riding
    over another climb first (e.g. Sa Calobra from Pollença, over the Coll de Femenia). Their distance is
    base -> near foot + the near climb + its top -> onward foot, so the score can rate them as further away.
Onward climbs count in the climbing score but not towards the gate: counted in the gate they let flat
places pass on the strength of hills beyond the hills (Valencia passed with 1 near + 3 onward).

  python pipeline/score/gate.py --places      named validation places: climbs within reach, nearest first
  python pipeline/score/gate.py --map         every junction's count of near climbs -> WORK/gate_counts.npy
"""
import heapq, json, math, os, sys, time
import numpy as np
from common import WORK
from graph import load, Snapper

GATE_N, REACH_KM = 3, 26.0
# name, lat, lon, expected ('pass' known cycling base / 'fail' flat)
PLACES = [
    ('Port de Pollença', 39.905, 3.087, 'pass'), ('Pollença', 39.877, 3.016, 'pass'), ('Sóller', 39.767, 2.715, 'pass'),
    ('Girona', 41.980, 2.820, 'pass'), ('Olot', 42.180, 2.490, 'pass'), ('Begur', 41.954, 3.207, '?'),
    ('Calpe', 38.645, 0.044, 'pass'), ('Dénia', 38.840, 0.105, 'pass'), ('Altea', 38.599, -0.051, 'pass'),
    ('Nerja', 36.746, -3.876, 'pass'), ('Torrox Costa', 36.728, -3.955, 'pass'), ('Cómpeta', 36.834, -3.973, 'pass'),
    ('Ronda', 36.742, -5.166, 'pass'), ('Granada', 37.177, -3.599, 'pass'), ('Jaca', 42.570, -0.549, 'pass'),
    ('Puerto de la Cruz (Tenerife)', 28.414, -16.548, 'pass'), ('San Bartolomé de Tirajana (Gran Canaria)', 27.925, -15.573, 'pass'),
    ('Marbella', 36.510, -4.885, '?'), ('Alicante', 38.345, -0.481, '?'), ('Palma', 39.570, 2.650, '?'),
    ('Deltebre (Ebro Delta)', 40.720, 0.710, 'fail'), ('Tomelloso (La Mancha)', 39.157, -3.025, 'fail'),
    ('Matalascañas (Huelva coast)', 36.993, -6.529, 'fail'), ('Valencia', 39.470, -0.376, 'fail'),
    ('Lleida', 41.617, 0.620, 'fail'), ('Badajoz', 38.879, -6.970, 'fail'),
    ('Monchique', 37.317, -8.556, 'pass'), ('Covilhã (Serra da Estrela)', 40.281, -7.504, 'pass'), ('Sintra', 38.797, -9.388, '?'),
    ('Azeitão (Arrábida)', 38.518, -9.013, '?'), ('Vila do Gerês', 41.727, -8.163, 'pass'), ('Funchal (Madeira)', 32.650, -16.908, 'pass'),
    ('Aveiro', 40.640, -8.654, 'fail'), ('Beja', 38.015, -7.865, 'fail'),
]

def adjacency(d, g, reverse=False):
    """Per-junction lists of (neighbour, metres) for riding forwards, or for reaching a junction (reverse)."""
    src, dst = np.array(g.get_edgelist()).T
    w = np.array(g.es['w'])
    if reverse: src, dst = dst, src
    order = np.argsort(src, kind='stable'); src, dst, w = src[order], dst[order], w[order]
    start = np.searchsorted(src, np.arange(g.vcount() + 1))
    return start, dst.tolist(), w.tolist()

def within(start, nbr, w, source, limit):
    """Dijkstra from source up to limit metres: {junction: metres}."""
    dist = {source: 0.0}; heap = [(0.0, source)]
    while heap:
        dd, a = heapq.heappop(heap)
        if dd > dist.get(a, math.inf): continue
        for i in range(start[a], start[a + 1]):
            nd = dd + w[i]
            if nd <= limit and nd < dist.get(nbr[i], math.inf):
                dist[nbr[i]] = nd; heapq.heappush(heap, (nd, nbr[i]))
    return dist

class Reach:
    """Near and onward climbs for any base."""
    def __init__(self, d, g, climbs):
        self.climbs = climbs
        self.snap = Snapper(d, g)
        self.adj = adjacency(d, g)
        self.foot_of = {}
        for i, c in enumerate(climbs): self.foot_of.setdefault(c['foot'], []).append(i)
        self.onward = {}   # climb index -> {other climb index: metres from its top to that foot}

    def near(self, node):
        reach = within(*self.adj, node, REACH_KM * 1000)
        return {i: reach[f] for f, ids in self.foot_of.items() if f in reach for i in ids}

    def from_top(self, i):
        if i not in self.onward:
            c = self.climbs[i]
            top, _ = self.snap(c['top_lat'], c['top_lon'])
            self.onward[i] = {j: dd for j, dd in self.near(top).items() if j != i}
        return self.onward[i]

    def __call__(self, node):
        """{climb index: (distance in metres, via climb index or None)}, near climbs first-choice."""
        out = {i: (dd, None) for i, dd in self.near(node).items()}
        for i, dd in list(out.items()):
            if dd[1] is not None: continue
            ride = dd[0] + self.climbs[i]['length_km'] * 1000
            for j, dj in self.from_top(i).items():
                tot = ride + dj
                if j not in out or (out[j][1] is not None and tot < out[j][0]): out[j] = (tot, i)
        return out

def places(d, g, climbs):
    R = Reach(d, g, climbs)
    summary = []
    for name, la, lo, expect in PLACES:
        node, off = R.snap(la, lo)
        found = sorted(R(node).items(), key=lambda x: x[1][0])
        near = [x for x in found if x[1][1] is None]; onward = [x for x in found if x[1][1] is not None]
        n = len(found); ok = len(near) >= GATE_N
        flag = '' if expect == '?' or (expect == 'pass') == ok else '   <-- unexpected'
        print(f"\n{name}: {'PASS' if ok else 'fail'} with {len(near)} near climbs (gate needs {GATE_N}); {len(onward)} more onward (expected {expect}){flag}")
        for i, (dist, via) in near[:5]:
            c = climbs[i]
            print(f"   near    {dist / 1000:5.1f} km to the foot: {c['gain']:.0f} m over {c['length_km']} km at {c['grade']}% (top {c['top_z']:.0f} m)")
        for i, (dist, via) in onward[:4]:
            c = climbs[i]; v = climbs[via]
            print(f"   onward  {dist / 1000:5.1f} km via the {v['gain']:.0f} m climb: {c['gain']:.0f} m over {c['length_km']} km at {c['grade']}% (top {c['top_z']:.0f} m)")
        if len(near) > 5 or len(onward) > 4: print(f"   ... {max(0, len(near) - 5)} more near, {max(0, len(onward) - 4)} more onward")
        summary.append((name, n, expect, ok))
    bad = [s for s in summary if s[2] != '?' and (s[2] == 'pass') != s[3]]
    print(f"\n{len(summary) - len(bad)} of {len(summary)} places as expected" + (f"; unexpected: {', '.join(s[0] for s in bad)}" if bad else ''))

def gate_map(d, g, climbs):
    start, nbr, w = adjacency(d, g, reverse=True)
    counts = np.zeros(g.vcount(), np.int32)
    t = time.time()
    for i, c in enumerate(climbs):
        for node in within(start, nbr, w, c['foot'], REACH_KM * 1000): counts[node] += 1
        if (i + 1) % 1000 == 0: print(f'  {i + 1:,} of {len(climbs):,} climbs ({time.time() - t:.0f} s)', flush=True)
    np.save(os.path.join(WORK, 'gate_counts.npy'), counts)
    print(f'junctions with >= {GATE_N} near climbs within {REACH_KM:.0f} km: {(counts >= GATE_N).mean():.1%} (onward climbs are added per base in phase 5)')

def main():
    d, g = load()
    climbs = json.load(open(os.path.join(WORK, 'climbs.json')))['climbs']
    if '--map' in sys.argv: gate_map(d, g, climbs)
    else: places(d, g, climbs)

if __name__ == '__main__':
    main()
