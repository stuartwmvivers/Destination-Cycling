#!/usr/bin/env python3
"""Drive time from every junction of the driving network (build_network.py --drive) to the nearest airport with
qualifying flights from Edinburgh or Glasgow (config/airports.json).

Speeds are typical per road class (DRIVE_SPEED in build_network.py), with no traffic: a rough estimate, checked
against known transfer times. Two variants are saved:
  year_round   airports with year-round flights from EDI or GLA (the spec's rule; full weight)
  any          also airports with seasonal flights (for information; the spec counts these much less in winter)
Output: WORK/drive_times.npz (minutes per drive junction, nearest airport code, drive junction coordinates).
Usage (score venv): python pipeline/score/drive_times.py [--check]
"""
import json, os, sys
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.spatial import cKDTree
from common import ROOT, WORK
from build_network import DRIVE_SPEED

def graph():
    d = np.load(os.path.join(WORK, 'drive.npz'))
    speed = np.array([DRIVE_SPEED[c] for c in d['classes']], float)
    u, v, one = d['edge_u'], d['edge_v'], d['edge_oneway']
    minutes = d['edge_len'] / (speed[d['edge_cls']] * 1000 / 60)
    back = one == 0
    src, dst, w = np.r_[u, v[back]], np.r_[v, u[back]], np.r_[minutes, minutes[back]]
    # keep the fastest of parallel edges (a sparse matrix would add them up)
    order = np.lexsort((w, dst, src)); src, dst, w = src[order], dst[order], w[order]
    first = np.r_[True, (src[1:] != src[:-1]) | (dst[1:] != dst[:-1])]
    n = len(d['node_lat'])
    m = sparse.csr_matrix((w[first], (src[first], dst[first])), shape=(n, n))
    return d, m

def main(check):
    d, m = graph()
    lat, lon = d['node_lat'], d['node_lon']
    ap = json.load(open(os.path.join(ROOT, 'config', 'airports.json'), encoding='utf-8'))['airports']
    # snap airports onto the main strongly connected piece of their island/mainland
    ncomp, lab = connected_components(m, directed=True, connection='strong')
    big = np.bincount(lab) >= 500
    core = np.flatnonzero(big[lab])
    tree = cKDTree(np.column_stack([lat[core], lon[core] * np.cos(np.radians(lat[core]))]))
    snap = lambda la, lo: int(core[tree.query([la, lo * np.cos(np.radians(la))])[1]])
    out = {}
    for variant, ok in [('year_round', lambda a: 'year_round' in (a['edi'], a['gla'])),
                        ('any', lambda a: any(x in ('year_round', 'seasonal') for x in (a['edi'], a['gla'])))]:
        sel = [a for a in ap if ok(a)]
        src = np.array([snap(a['lat'], a['lon']) for a in sel])
        # time from each junction TO an airport: search the reversed graph outwards from the airports
        dist, _, sources = dijkstra(m.T.tocsr(), indices=src, min_only=True, return_predecessors=True)
        code = np.array([a['code'] for a in sel])
        idx = np.searchsorted(src, sources) if False else None
        lookup = {int(s): c for s, c in zip(src, code)}
        nearest = np.array([lookup.get(int(s), '') for s in sources])
        out[variant] = (dist.astype(np.float32), nearest)
        print(f"{variant}: {len(sel)} airports ({', '.join(a['code'] for a in sel)}); "
              f"junctions within 60 / 120 min: {(dist <= 60).mean():.0%} / {(dist <= 120).mean():.0%}; unreachable (islands without one): {np.isinf(dist).mean():.0%}")
    np.savez_compressed(os.path.join(WORK, 'drive_times.npz'), lat=lat.astype(np.float32), lon=lon.astype(np.float32), core=core,
                        yr_min=out['year_round'][0], yr_code=out['year_round'][1], any_min=out['any'][0], any_code=out['any'][1])
    if check:
        PLACES = [('Port de Pollença', 39.905, 3.087), ('Sóller', 39.767, 2.715), ('Girona', 41.980, 2.820), ('Calpe', 38.645, 0.044),
                  ('Torrox Costa', 36.728, -3.955), ('Nerja', 36.746, -3.876), ('Ronda', 36.742, -5.166), ('Granada', 37.177, -3.599),
                  ('Jaca', 42.570, -0.549), ('Olot', 42.180, 2.490), ('Puerto de la Cruz', 28.414, -16.548), ('Benidorm', 38.541, -0.131)]
        for name, la, lo in PLACES:
            j = snap(la, lo)
            yr, yc, an, ac = out['year_round'][0][j], out['year_round'][1][j], out['any'][0][j], out['any'][1][j]
            fmt = lambda x: 'none reachable' if np.isinf(x) else f'{x:.0f} min'
            print(f"  {name:18} year-round: {fmt(yr):>15} ({yc or '-'})   incl. seasonal: {fmt(an):>15} ({ac or '-'})")

if __name__ == '__main__':
    main('--check' in sys.argv)
