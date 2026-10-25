#!/usr/bin/env python3
"""Diagnostic: the height profile along the shortest legal bike route between two points, with the largest
dip below the running maximum. Used to see why a known climb is or isn't found.
Usage (score venv): python pipeline/score/trace_route.py LAT1 LON1 LAT2 LON2 [every_m]
"""
import os, sys
import numpy as np
from common import WORK
from graph import load, Snapper

def main():
    la1, lo1, la2, lo2 = map(float, sys.argv[1:5]); every = float(sys.argv[5]) if len(sys.argv) > 5 else 250
    d, g = load(); snap = Snapper(d, g)
    p = np.load(os.path.join(WORK, 'profiles.npz')); off, pd, pz = p['prof_off'], p['prof_d'], p['prof_z']
    a, _ = snap(la1, lo1); b, _ = snap(la2, lo2)
    epath = g.get_shortest_paths(a, b, weights='w', output='epath')[0]
    nu = len(d['edge_u'])
    dist, zs, cls = [], [], []
    total = 0.0
    for ge in epath:
        e = ge if ge < nu else np.flatnonzero(d['edge_oneway'] == 0)[ge - nu]   # reverse copies come after the forward edges
        src = g.es[ge].source
        z = pz[off[e]:off[e + 1]].astype(float); dd = pd[off[e]:off[e + 1]].astype(float)
        if src != d['edge_u'][e]: z = z[::-1]; dd = dd[-1] - dd[::-1]
        for i in range(len(z)):
            if dist and i == 0: continue
            dist.append(total + dd[i]); zs.append(z[i]); cls.append(str(d['classes'][d['edge_cls'][e]]))
        total += dd[-1]
    dist, zs = np.array(dist), np.array(zs)
    run = np.maximum.accumulate(zs); dip = run - zs
    print(f'route {total / 1000:.2f} km, from {zs[0]:.0f} m to {zs[-1]:.0f} m, highest {zs.max():.0f} m; largest dip below running max {dip.max():.0f} m at {dist[dip.argmax()] / 1000:.2f} km')
    nxt = 0.0
    for x, z, r, c in zip(dist, zs, dip, cls):
        if x >= nxt or r >= 20:
            print(f'{x / 1000:6.2f} km {z:6.0f} m  dip {r:4.0f}  {c}{"   <-- dip >= 20" if r >= 20 else ""}')
            nxt = x + every

if __name__ == '__main__':
    main()
