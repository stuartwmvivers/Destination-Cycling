#!/usr/bin/env python3
"""Build the cyclable paved road network for the score pipeline from the OSM extracts in the cache.

Keeps paved roads a cyclist may use: highway primary..unclassified (and links), residential, living_street,
road, and paved cycleways. Drops motorways, trunk roads marked motorroad=yes or bicycle=no, access/bicycle
= no/private, and unpaved surfaces. One-way streets are one-way unless oneway:bicycle=no.

Ways are split at junctions (nodes shared by two or more kept ways, plus way ends) into edges. Output,
in the cache (WORK/network.npz):
  node_lat, node_lon      junction coordinates (degrees)
  edge_u, edge_v          junction indices; edges run u -> v along the OSM way
  edge_len                length in metres
  edge_cls                road class code (index into CLASSES)
  edge_oneway             1 if only u -> v is allowed for bikes
  geom_off, geom_lat, geom_lon   the full polyline of each edge (geom_off[i]:geom_off[i+1]), for terrain sampling
Usage (score venv): python pipeline/score/build_network.py
"""
import glob, math, os, time
from array import array
import numpy as np
import osmium
from common import OSM, WORK

CLASSES = ['primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link', 'unclassified',
           'residential', 'living_street', 'road', 'cycleway', 'trunk', 'trunk_link']
CLS = {c: i for i, c in enumerate(CLASSES)}
UNPAVED = {'unpaved', 'gravel', 'fine_gravel', 'compacted', 'dirt', 'earth', 'ground', 'grass', 'sand', 'mud',
           'pebblestone', 'rock', 'wood', 'woodchips', 'grass_paver', 'clay', 'shells'}
NO = {'no', 'private', 'military'}

def keep(tags):
    h = tags.get('highway')
    if h not in CLS: return False
    if tags.get('access') in NO and tags.get('bicycle') not in ('yes', 'designated', 'permissive'): return False
    if tags.get('bicycle') in ('no', 'use_sidepath'): return False
    if h.startswith('trunk') and (tags.get('motorroad') == 'yes' or tags.get('bicycle') != 'yes' and tags.get('expressway') == 'yes'): return False
    if tags.get('surface') in UNPAVED: return False
    if h == 'cycleway' and tags.get('surface') is None and tags.get('tracktype'): return False
    if tags.get('area') == 'yes': return False
    return True

def oneway(tags):
    if tags.get('oneway:bicycle') == 'no' or tags.get('cycleway') in ('opposite', 'opposite_lane'): return 0
    o = tags.get('oneway')
    if o in ('yes', 'true', '1') or tags.get('junction') in ('roundabout', 'circular'): return 1
    if o == '-1': return -1
    return 0

def read_ways(path):
    """Way node ids and coordinates for kept ways, as flat arrays plus per-way offsets and attributes."""
    ids, lat, lon, off, cls, ow = array('q'), array('d'), array('d'), array('q', [0]), array('b'), array('b')
    fp = osmium.FileProcessor(path).with_locations().with_filter(osmium.filter.KeyFilter('highway'))
    for o in fp:
        if not o.is_way() or not keep(o.tags): continue
        refs = [(n.ref, n.lat, n.lon) for n in o.nodes if n.location.valid()]
        if len(refs) < 2: continue
        d = oneway(o.tags)
        if d == -1: refs.reverse(); d = 1
        for r, la, lo in refs: ids.append(r); lat.append(la); lon.append(lo)
        off.append(len(ids)); cls.append(CLS[o.tags['highway']]); ow.append(d)
    return (np.frombuffer(ids, np.int64), np.frombuffer(lat, np.float64), np.frombuffer(lon, np.float64),
            np.frombuffer(off, np.int64), np.frombuffer(cls, np.int8), np.frombuffer(ow, np.int8))

def haversine(la1, lo1, la2, lo2):
    p1, p2 = np.radians(la1), np.radians(la2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lo2 - lo1) / 2) ** 2
    return 2 * 6371008.8 * np.arcsin(np.sqrt(a))

def main():
    parts = []
    for f in sorted(glob.glob(os.path.join(OSM, '*-latest.osm.pbf'))):
        t = time.time(); parts.append(read_ways(f))
        print(f'{os.path.basename(f)}: {len(parts[-1][3]) - 1:,} ways kept ({time.time() - t:.0f} s)', flush=True)
    ids = np.concatenate([p[0] for p in parts]); lat = np.concatenate([p[1] for p in parts]); lon = np.concatenate([p[2] for p in parts])
    offs, base = [], 0
    for p in parts: offs.append(p[3][:-1] + base); base += len(p[0])
    off = np.append(np.concatenate(offs), base)
    cls = np.concatenate([p[4] for p in parts]); ow = np.concatenate([p[5] for p in parts])

    # junctions: nodes used more than once across kept ways, plus every way's first and last node
    uniq, inv, counts = np.unique(ids, return_inverse=True, return_counts=True)
    is_end = np.zeros(len(ids), bool); is_end[off[:-1]] = True; is_end[off[1:] - 1] = True
    junction = (counts[inv] > 1) | is_end
    jid = np.full(len(uniq), -1, np.int64)
    jnodes = np.unique(inv[junction]); jid[jnodes] = np.arange(len(jnodes))
    node_lat = np.zeros(len(jnodes)); node_lon = np.zeros(len(jnodes))
    node_lat[jid[inv[junction]]] = lat[junction]; node_lon[jid[inv[junction]]] = lon[junction]

    seg = haversine(lat[:-1], lon[:-1], lat[1:], lon[1:])   # metres between consecutive points (across ways too; masked below)
    eu, ev, el, ec, eo, goff = array('q'), array('q'), array('d'), array('b'), array('b'), array('q', [0])
    gsel = np.zeros(len(ids), bool); glen = 0
    for w in range(len(off) - 1):
        a, b = off[w], off[w + 1]
        cuts = np.flatnonzero(junction[a:b]) + a
        for s, e in zip(cuts[:-1], cuts[1:]):
            eu.append(jid[inv[s]]); ev.append(jid[inv[e]]); el.append(float(seg[s:e].sum())); ec.append(cls[w]); eo.append(ow[w])
            glen += e - s + 1; goff.append(glen)
    # geometry: every edge's points s..e inclusive (shared junction points repeated per edge)
    geom_idx = np.empty(glen, np.int64); k = 0
    for w in range(len(off) - 1):
        a, b = off[w], off[w + 1]
        cuts = np.flatnonzero(junction[a:b]) + a
        for s, e in zip(cuts[:-1], cuts[1:]):
            n = e - s + 1; geom_idx[k:k + n] = np.arange(s, e + 1); k += n
    out = os.path.join(WORK, 'network.npz')
    np.savez_compressed(out, node_lat=node_lat, node_lon=node_lon, edge_u=np.frombuffer(eu, np.int64), edge_v=np.frombuffer(ev, np.int64),
                        edge_len=np.frombuffer(el, np.float64), edge_cls=np.frombuffer(ec, np.int8), edge_oneway=np.frombuffer(eo, np.int8),
                        geom_off=np.frombuffer(goff, np.int64), geom_lat=lat[geom_idx].astype(np.float32), geom_lon=lon[geom_idx].astype(np.float32),
                        classes=np.array(CLASSES))
    print(f'network: {len(jnodes):,} junctions, {len(eu):,} edges, {sum(el) / 1000:,.0f} km of road -> {out} ({os.path.getsize(out) / 1e6:.0f} MB)')

if __name__ == '__main__':
    main()
