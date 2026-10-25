#!/usr/bin/env python3
"""Find road climbs on the cyclable network (build_network.py + sample_terrain.py).

A climb (spec section 8, owner 24 Oct 2026): >= 300 m of continuous ascent on paved roads, where a dip of
under 20 m below the highest point so far doesn't break it. Practical rules added, all tunable:
  - progress: at least PROG_RISE metres of new height every PROG_DIST metres, so a climb can include a
    flat or dipping stretch (e.g. past the Mirador de Ses Barques on Puig Major) but not an endless plateau;
  - foot trimming: afterwards, the foot moves up past any opening stretch that gains less than TRIM_RISE
    over the next TRIM_DIST (a gentle approach, e.g. Pollença towards the Coll de Femenia, isn't climbing);
  - average gradient >= MIN_GRADE over the (trimmed) climb.
One-way streets are respected (a climb is ridden in a legal direction).

Search: states (foot, highest point so far, ...) spread from every junction along legal directions, in
order of foot height, so each junction keeps the lowest feet from which a valid climb reaches it: up to K,
whose feet are >= FOOT_SEP apart (so both sides of a pass survive). Each foot's climb ends at the highest
point any of its states reached, including partway along a road stretch where a dip or a stall ends the
climb before the next junction (long stretches without junctions are common on mountain roads). Climbs whose foot lies on a bigger climb's path (the upper part of the
same climb) or that share more than half their road length with a bigger climb ending nearby are dropped.

Output: cache WORK/climbs.json, plus a summary. Usage (score venv):
  python pipeline/score/find_climbs.py                       all of Spain
  python pipeline/score/find_climbs.py --bbox S W N E        a test area, e.g. Mallorca 39.2 2.3 40.0 3.5
"""
import heapq, json, math, os, sys, time
from array import array
import numpy as np
from common import WORK

MIN_GAIN, DIP, PROG_RISE, PROG_DIST, MIN_GRADE = 300.0, 20.0, 5.0, 1000.0, 0.03
TRIM_RISE, TRIM_DIST = 15.0, 500.0
K, FOOT_SEP = 3, 1500.0

def load(bbox):
    n = np.load(os.path.join(WORK, 'network.npz')); p = np.load(os.path.join(WORK, 'profiles.npz'))
    lat, lon = n['node_lat'], n['node_lon']
    u, v, one = n['edge_u'], n['edge_v'], n['edge_oneway']
    keep_node = np.ones(len(lat), bool) if bbox is None else ((lat >= bbox[0]) & (lat <= bbox[2]) & (lon >= bbox[1]) & (lon <= bbox[3]))
    ke = keep_node[u] & keep_node[v]
    # directed transitions: (from, to, edge, reversed?)
    ef = np.flatnonzero(ke); eb = np.flatnonzero(ke & (one == 0))
    t_from = np.r_[u[ef], v[eb]]; t_to = np.r_[v[ef], u[eb]]; t_edge = np.r_[ef, eb]; t_rev = np.r_[np.zeros(len(ef), bool), np.ones(len(eb), bool)]
    order = np.argsort(t_from, kind='stable')
    t_from, t_to, t_edge, t_rev = t_from[order], t_to[order], t_edge[order], t_rev[order]
    start = np.searchsorted(t_from, np.arange(len(lat) + 1))
    off, pd, pz = p['prof_off'], p['prof_d'], p['prof_z']
    node_z = np.full(len(lat), np.nan, np.float32)
    node_z[u] = pz[off[:-1]]; node_z[v] = pz[off[1:] - 1]
    return dict(lat=lat, lon=lon, node_z=node_z, keep=keep_node, edge_u_=u, edge_v_=v, start=start, t_to=t_to, t_edge=t_edge, t_rev=t_rev,
                off=off, pd=pd, pz=pz, edge_len=n['edge_len'], goff=n['geom_off'], glat=n['geom_lat'], glon=n['geom_lon'])

def search(G):
    lat, lon, nz = G['lat'], G['lon'], G['node_z'].tolist()
    start, t_to, t_edge, t_rev = G['start'], G['t_to'].tolist(), G['t_edge'].tolist(), G['t_rev'].tolist()
    off, pd, pz = G['off'], G['pd'], G['pz']
    coslat = math.cos(math.radians(float(np.mean(lat[G['keep']]))))
    LAT, LON = (lat * 111195.0).tolist(), (lon * 111195.0 * coslat).tolist()
    # accepted states, columnar
    S_node, S_foot, S_pred = array('q'), array('q'), array('q')
    S_F, S_R, S_cz, S_cd, S_L, S_LR = (array('d') for _ in range(6))
    S_Re, S_Rd = array('q'), array('d')                       # where the highest point is: edge, distance along it (forward frame)
    at = {}                                                   # node -> list of foot nodes accepted there
    best = {}                                                 # foot -> state id with the highest R
    tops = {}                                                 # foot -> (R, LR, Re, Rd, pred state) for climbs ending partway along an edge
    heap = [(nz[i], i) for i in np.flatnonzero(G['keep'] & ~np.isnan(G['node_z'])).tolist()]
    heapq.heapify(heap)
    # heap items: (F, x): x >= 0 is a junction to start a climb from; x < 0 is accepted state -x-1 to expand

    def accept(node, foot, F, R, cz, cd, L, LR, Re, Rd, pred):
        feet = at.get(node)
        if feet is not None:
            if len(feet) >= K: return False
            fx, fy = LAT[foot], LON[foot]
            for f in feet:
                if (LAT[f] - fx) ** 2 + (LON[f] - fy) ** 2 < FOOT_SEP ** 2: return False
            feet.append(foot)
        else:
            at[node] = [foot]
        sid = len(S_node)
        S_node.append(node); S_foot.append(foot); S_pred.append(pred); S_F.append(F); S_R.append(R); S_cz.append(cz)
        S_cd.append(cd); S_L.append(L); S_LR.append(LR); S_Re.append(Re); S_Rd.append(Rd)
        b = best.get(foot)
        if b is None or R > S_R[b]: best[foot] = sid
        heapq.heappush(heap, (F, -sid - 1))
        return True

    popped = 0
    while heap:
        F, x = heapq.heappop(heap); popped += 1
        if x >= 0:
            accept(x, x, F, F, F, 0.0, 0.0, 0.0, -1, 0.0, -1)
            continue
        s = -x - 1
        a, foot, R, cz, cd, L, LR, Re, Rd = S_node[s], S_foot[s], S_R[s], S_cz[s], S_cd[s], S_L[s], S_LR[s], S_Re[s], S_Rd[s]
        for t in range(start[a], start[a + 1]):
            e = t_edge[t]; o0, o1 = off[e], off[e + 1]
            z = pz[o0:o1].tolist(); d = pd[o0:o1].tolist(); elen = d[-1]
            if t_rev[t]: z.reverse(); d = [elen - x_ for x_ in reversed(d)]
            r, c_z, c_d, l, lr, re_, rd = R, cz, cd, L, LR, Re, Rd
            ok = True
            for i in range(1, len(z)):
                l += d[i] - d[i - 1]; zi = z[i]
                if zi > r:
                    r = zi; lr = l; re_ = e; rd = (elen - d[i]) if t_rev[t] else d[i]
                    if r >= c_z + PROG_RISE: c_z = r; c_d = l
                elif r - zi >= DIP: ok = False; break
                if l - c_d > PROG_DIST: ok = False; break
            if ok:
                accept(t_to[t], foot, F, r, c_z, c_d, l, lr, re_, rd, s)
            elif r > R:   # climbed higher along this edge before it failed: the climb may top out here
                cur = tops.get(foot)
                if cur is None or r > cur[0]: tops[foot] = (r, lr, re_, rd, s)
    return dict(node=S_node, foot=S_foot, pred=S_pred, F=S_F, R=S_R, LR=S_LR, Re=S_Re, Rd=S_Rd), best, tops, popped

def point_on_edge(G, e, dist):
    """Coordinates at a distance along an edge (forward frame), from its road shape."""
    a, b = G['goff'][e], G['goff'][e + 1]
    la, lo = G['glat'][a:b].astype(float), G['glon'][a:b].astype(float)
    seg = np.hypot(np.diff(la) * 111195.0, np.diff(lo) * 111195.0 * np.cos(np.radians(la[:-1])))
    cum = np.r_[0, np.cumsum(seg)]
    if cum[-1] <= 0: return float(la[0]), float(lo[0])
    x = min(max(dist / max(G['edge_len'][e], 1e-9) * cum[-1], 0), cum[-1])
    i = min(np.searchsorted(cum, x, side='right') - 1, len(seg) - 1)
    f = (x - cum[i]) / seg[i] if seg[i] > 0 else 0
    return float(la[i] + f * (la[i + 1] - la[i])), float(lo[i] + f * (lo[i + 1] - lo[i]))

def transition(G, a, b):
    """The (edge, reversed) of the shortest legal transition from junction a to junction b."""
    best = None
    for t in range(G['start'][a], G['start'][a + 1]):
        if G['t_to'][t] == b:
            e = int(G['t_edge'][t])
            if best is None or G['edge_len'][e] < G['edge_len'][best[0]]: best = (e, bool(G['t_rev'][t]))
    return best

def edge_profile(G, e, rev):
    o0, o1 = G['off'][e], G['off'][e + 1]
    z = G['pz'][o0:o1].astype(float); d = G['pd'][o0:o1].astype(float)
    if rev: z = z[::-1]; d = d[-1] - d[::-1]
    return d, z

def climb_profile(G, path, Re, Rd):
    """Distance and height along a climb's junction path, ending at its top (which may be partway along the
    edge after the last junction). Also the profile index of each junction in the path."""
    dist, z, jpos, total = [0.0], [float(G['node_z'][path[0]])], [0], 0.0
    for a, b in zip(path[:-1], path[1:]):
        e, rev = transition(G, a, b)
        d, zz = edge_profile(G, e, rev)
        dist.extend((total + d[1:]).tolist()); z.extend(zz[1:].tolist()); total += d[-1]; jpos.append(len(dist) - 1)
    if Re >= 0:   # top partway along an edge leaving the last junction
        e = Re
        u, v = G['edge_u_'][e], G['edge_v_'][e]
        rev = (v == path[-1])
        if u == path[-1] or v == path[-1]:
            d, zz = edge_profile(G, e, rev)
            to = (G['edge_len'][e] - Rd) if rev else Rd
            m = d <= to + 1e-6
            dist.extend((total + d[1:][m[1:]]).tolist()); z.extend(zz[1:][m[1:]].tolist())
    # cut at the highest point
    top = int(np.argmax(z))
    return np.array(dist[:top + 1]), np.array(z[:top + 1]), [p for p in jpos if p <= top] or [0]

def trim_start(dist, z):
    """Index of the first point from which the next TRIM_DIST gains at least TRIM_RISE."""
    j = 0
    for i in range(len(z)):
        while j < len(z) - 1 and dist[j] < dist[i] + TRIM_DIST: j += 1
        if z[j] - z[i] >= TRIM_RISE or dist[j] - dist[i] < TRIM_DIST: return i
    return 0

def climbs_from(G, S, best, tops):
    cands = []
    for foot in set(best) | set(tops):
        sid = best.get(foot)
        if sid is not None:
            F, R, LR, Re, Rd, last = S['F'][sid], S['R'][sid], S['LR'][sid], S['Re'][sid], S['Rd'][sid], sid
        if foot in tops and (sid is None or tops[foot][0] > R):
            R, LR, Re, Rd, last = tops[foot]; F = S['F'][last]
        if R - F < MIN_GAIN or LR <= 0: continue
        # path: junctions from the foot up to the last one before the top
        path, s = [], last
        while s >= 0: path.append(S['node'][s]); s = S['pred'][s]
        path.reverse()
        dist, z, jpos = climb_profile(G, path, Re, Rd)
        i = trim_start(dist, z)
        # the trimmed foot: the last junction at or before the trimmed start
        k = max(j for j, pos in enumerate(jpos) if pos <= i)
        fnode, fd = path[k], dist[jpos[k]]
        top_d = dist[-1]; F2 = float(z[jpos[k]]); gain = R - F2; length = top_d - fd
        if gain < MIN_GAIN or length <= 0 or gain / length < MIN_GRADE: continue
        tlat, tlon = point_on_edge(G, Re, Rd) if Re >= 0 else (float(G['lat'][fnode]), float(G['lon'][fnode]))
        cands.append(dict(foot=int(fnode), foot_lat=float(G['lat'][fnode]), foot_lon=float(G['lon'][fnode]), foot_z=round(F2, 1),
                          top_lat=round(tlat, 6), top_lon=round(tlon, 6), top_z=round(float(R), 1), gain=round(float(gain), 1),
                          length_km=round(float(length) / 1000, 2), grade=round(float(gain / length) * 100, 1), path=path[k:]))
    cands.sort(key=lambda c: -c['gain'])
    def legs(path):   # road length per junction-to-junction leg of a climb's path
        out = {}
        for a, b in zip(path[:-1], path[1:]):
            t = transition(G, a, b)
            if t: out[(a, b)] = float(G['edge_len'][t[0]])
        return out
    kept, kept_legs = [], []
    for c in cands:
        cl = legs(c['path']); clen = sum(cl.values()) or 1.0
        dup = False
        for k, kl in zip(kept, kept_legs):
            if c['foot'] in {a for a, _ in kl} | {b for _, b in kl}:          # starts on the bigger climb: its upper part
                dup = True; break
            near_top = (k['top_lat'] - c['top_lat']) ** 2 + ((k['top_lon'] - c['top_lon']) * math.cos(math.radians(c['top_lat']))) ** 2 < (1.5 / 111.2) ** 2
            if near_top and sum(v for key, v in cl.items() if key in kl) > 0.5 * clen:   # mostly the same road
                dup = True; break
        if not dup:
            kept.append(c); kept_legs.append(cl)
    for c in kept: c['path_len'] = len(c.pop('path'))
    return kept

def main():
    a = sys.argv[1:]
    bbox = [float(x) for x in a[a.index('--bbox') + 1:a.index('--bbox') + 5]] if '--bbox' in a else None
    t = time.time(); G = load(bbox)
    print(f'loaded: {int(G["keep"].sum()):,} junctions, {len(G["t_to"]):,} directed edges ({time.time() - t:.0f} s)', flush=True)
    S, best, tops, popped = search(G)
    print(f'search: {len(S["node"]):,} accepted states, {popped:,} heap pops ({time.time() - t:.0f} s)', flush=True)
    climbs = climbs_from(G, S, best, tops)
    name = 'climbs.json' if bbox is None else 'climbs_test.json'
    json.dump({'rules': dict(min_gain=MIN_GAIN, dip=DIP, prog_rise=PROG_RISE, prog_dist=PROG_DIST, trim_rise=TRIM_RISE, trim_dist=TRIM_DIST,
                             min_grade=MIN_GRADE, k=K, foot_sep=FOOT_SEP),
               'bbox': bbox, 'climbs': climbs}, open(os.path.join(WORK, name), 'w'))
    print(f'{len(climbs):,} climbs >= {MIN_GAIN:.0f} m -> {name} ({time.time() - t:.0f} s)')

if __name__ == '__main__':
    main()
