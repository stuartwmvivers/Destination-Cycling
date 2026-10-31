#!/usr/bin/env python3
"""Join the private property prices onto the score's bases (phase 6; docs/price-data-plan.md, docs/portugal-plan.md).

Inputs: data/private/prices.json (git-ignored): notaries' portal average price per m2 per Spanish municipality, looked
        up by hand-paced searches for the shortlist (price_shortlist.py);
        CACHE/prices-portugal/ine_0012234.json: Statistics Portugal's median price per m2 of sales in the last 12
        months, all homes, for every municipality (kept private too, by the owner's decision);
        WORK/municipalities.json.
Output: data/private/score_prices.json (git-ignored), aligned with data/processed/score/bases.json's bases:
        eur_m2 (or null when the base's own municipality hasn't been looked up: no borrowing from neighbours),
        and a small table of the municipalities with their names, sources and check dates.
Only `python build/build_site.py --private` reads it; the public build never does.
Usage (score venv): python pipeline/score/price_join.py
"""
import json, os
from common import CACHE, ROOT, SCORE_JSON, WORK
from price_shortlist import province

PRIVATE = os.path.join(ROOT, 'data', 'private')
INE_PT = 'Statistics Portugal (INE), indicator 0012234, median price per m2 of sales in the last 12 months'

def portugal(mu):
    """{'PT0809': entry} from the INE download. Geocodes of 7 characters are municipalities and end in the 4-digit code."""
    d = json.load(open(os.path.join(CACHE, 'prices-portugal', 'ine_0012234.json'), encoding='utf-8'))[0]
    period, rows = next(iter(d['Dados'].items()))
    names = {m['ine']: m['name'] for m in mu['munis'] if m['ine'].startswith('PT')}
    out = {}
    for r in rows:
        k = 'PT' + r['geocod'][-4:]
        if len(r['geocod']) != 7 or r['dim_3_t'] != 'Total' or k not in names: continue
        v = r.get('valor')
        out[k] = {'name': names[k], 'province': province(k), 'eur_m2': round(float(v)) if v else None, 'checked': period, 'src': 'ine'}
    return out

def main():
    prices = json.load(open(os.path.join(PRIVATE, 'prices.json'), encoding='utf-8'))
    mu = json.load(open(os.path.join(WORK, 'municipalities.json'), encoding='utf-8'))
    n = len(json.load(open(SCORE_JSON, encoding='utf-8'))['bases']['lat'])
    assert len(mu['base_muni']) == n, 'municipalities.json is out of date: rerun municipalities.py'
    looked = {v['ine']: {'name': v['portal_name'], 'province': v['portal_province'], 'eur_m2': v['eur_m2'], 'checked': v['checked'], 'src': 'notaries'}
              for v in prices['prices'].values()}
    looked.update(portugal(mu))
    munis = {k: v for k, v in looked.items() if v['eur_m2']}
    keys = sorted(munis)
    slot = {k: i for i, k in enumerate(keys)}
    code = [mu['munis'][m]['ine'] if m >= 0 else '' for m in mu['base_muni']]
    out = {'source': f"{prices['source']}. Portugal: {INE_PT}",
           'munis': [munis[k] for k in keys],
           'base_muni': [slot.get(k, -2 if k in looked else -1) for k in code]}   # -2: looked up, too few sales
    json.dump(out, open(os.path.join(PRIVATE, 'score_prices.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    pt = sum(k.startswith('PT') for k in keys)
    print(f"{len(keys)} municipalities with a price ({pt} in Portugal); {sum(s >= 0 for s in out['base_muni']):,} of {n:,} bases priced -> data/private/score_prices.json")

if __name__ == '__main__':
    main()
