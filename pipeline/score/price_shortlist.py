#!/usr/bin/env python3
"""Municipalities to look up on the notaries' price portal (phase 6; docs/price-data-plan.md).

Takes the best N bases under the page's default settings (agreed weights, year-round flights, gate 3, built-up
penalty 20%), one per SPREAD_KM as the page's "one per area" list, plus the validation places, and lists their
municipalities (municipalities.py), best first. Prices are private: the lookups and their results never go in git.
Output: WORK/price_shortlist.json.  Usage (score venv): python pipeline/score/price_shortlist.py [N]   (default 150)
"""
import json, math, os, sys
from common import ROOT, WORK

SPREAD_KM = 15
PROVINCES = {'01': 'Araba/Álava', '02': 'Albacete', '03': 'Alicante', '04': 'Almería', '05': 'Ávila', '06': 'Badajoz', '07': 'Illes Balears',
             '08': 'Barcelona', '09': 'Burgos', '10': 'Cáceres', '11': 'Cádiz', '12': 'Castellón', '13': 'Ciudad Real', '14': 'Córdoba', '15': 'A Coruña',
             '16': 'Cuenca', '17': 'Girona', '18': 'Granada', '19': 'Guadalajara', '20': 'Gipuzkoa', '21': 'Huelva', '22': 'Huesca', '23': 'Jaén',
             '24': 'León', '25': 'Lleida', '26': 'La Rioja', '27': 'Lugo', '28': 'Madrid', '29': 'Málaga', '30': 'Murcia', '31': 'Navarra',
             '32': 'Ourense', '33': 'Asturias', '34': 'Palencia', '35': 'Las Palmas', '36': 'Pontevedra', '37': 'Salamanca', '38': 'Santa Cruz de Tenerife',
             '39': 'Cantabria', '40': 'Segovia', '41': 'Sevilla', '42': 'Soria', '43': 'Tarragona', '44': 'Teruel', '45': 'Toledo', '46': 'Valencia',
             '47': 'Valladolid', '48': 'Bizkaia', '49': 'Zamora', '50': 'Zaragoza', '51': 'Ceuta', '52': 'Melilla'}

def airport_curve(m):
    if m is None: return 0.15
    return 1 if m <= 60 else 1 - .5 * (m - 60) / 60 if m <= 120 else .15 + .35 * math.exp(-(m - 120) / 60)

def main(n_top):
    d = json.load(open(os.path.join(ROOT, 'data', 'processed', 'score', 'spain.json'), encoding='utf-8'))
    B, W = d['bases'], d['weights']; N = len(B['lat'])
    mu = json.load(open(os.path.join(WORK, 'municipalities.json'), encoding='utf-8'))
    total = [sum(W[k] * ((B['c_' + k][i] or 0) if k != 'airport' else airport_curve(B['yr_min'][i])) for k in W) / sum(W.values()) * 100
             * (1 - d['built']['strength'] * (B['c_built'][i] or 0)) for i in range(N)]
    order = sorted((i for i in range(N) if len(B['near'][i]) >= d['gate_n']), key=lambda i: -total[i])
    rank = {i: r + 1 for r, i in enumerate(order)}
    km = lambda i, j: math.hypot(B['lat'][i] - B['lat'][j], (B['lon'][i] - B['lon'][j]) * math.cos(math.radians(B['lat'][i]))) * 111.2
    top = []
    for i in order:
        if all(km(i, j) > SPREAD_KM for j in top): top.append(i)
        if len(top) >= n_top: break
    known = [min(range(N), key=lambda i: (B['lat'][i] - p['lat']) ** 2 + ((B['lon'][i] - p['lon']) * math.cos(math.radians(p['lat']))) ** 2) for p in d['places']]
    out, seen = [], set()
    for why, i in [('top', i) for i in top] + [('known place', i) for i in known]:
        m = mu['base_muni'][i]
        if m < 0 or m in seen: continue
        seen.add(m); mm = mu['munis'][m]
        out.append({'muni': m, 'name': mm['name'], 'ine': mm['ine'], 'province': PROVINCES.get(mm['ine'][:2], ''),
                    'why': why, 'best_rank': rank.get(i), 'base': B['name'][i]})
    json.dump({'n_top': n_top, 'spread_km': SPREAD_KM, 'municipalities': out}, open(os.path.join(WORK, 'price_shortlist.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(out)} municipalities from the best {len(top)} areas and {len(known)} known places -> WORK/price_shortlist.json')
    for m in out[:12]: print(f"  {m['best_rank'] or '-':>5} {m['name']} ({m['province']})")

if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 150)
