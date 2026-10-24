"""Load the road network (build_network.py) as a directed igraph, and snap places onto it.

Snapping uses only junctions in a large strongly connected component (one per island or mainland), i.e.
places you can both reach and leave by bike. About 7% of junctions are one-way stubs or traps (often town
centres where the onward street is pedestrian, or tagging quirks); snapping a base onto one of those made
whole towns look unreachable.
"""
import os
import numpy as np, igraph as ig
from scipy.spatial import cKDTree
from common import WORK

MIN_CORE = 500   # junctions; smaller strongly connected pieces are stubs, not a usable network

def load():
    """(arrays from network.npz, directed graph with edge weight 'w' in metres)."""
    d = dict(np.load(os.path.join(WORK, 'network.npz')))
    u, v, w, one = d['edge_u'], d['edge_v'], d['edge_len'], d['edge_oneway']
    back = one == 0   # two-way for bikes: add the reverse direction
    g = ig.Graph(n=len(d['node_lat']), edges=np.column_stack([np.r_[u, v[back]], np.r_[v, u[back]]]).tolist(), directed=True)
    g.es['w'] = np.r_[w, w[back]].tolist()
    return d, g

class Snapper:
    """Nearest usable junction to a point."""
    def __init__(self, d, g):
        scc = g.connected_components(mode='strong')
        sizes = np.array(scc.sizes()); memb = np.array(scc.membership)
        self.core = np.flatnonzero(sizes[memb] >= MIN_CORE)
        lat, lon = d['node_lat'][self.core], d['node_lon'][self.core]
        self.tree = cKDTree(np.column_stack([lat, lon * np.cos(np.radians(lat))]))

    def __call__(self, lat, lon):
        """(junction index, distance in km) for a point."""
        dist, i = self.tree.query([lat, lon * np.cos(np.radians(lat))])
        return int(self.core[i]), dist * 111.2
