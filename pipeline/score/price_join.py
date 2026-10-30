#!/usr/bin/env python3
"""Join the private property prices onto the score's bases (phase 6; docs/price-data-plan.md).

Input:  data/private/prices.json (git-ignored): notaries' portal average price per m2 per municipality, looked up
        by hand-paced searches for the shortlist (price_shortlist.py); WORK/municipalities.json.
Output: data/private/score_prices.json (git-ignored), aligned with data/processed/score/spain.json's bases:
        eur_m2 (or null when the base's own municipality hasn't been looked up: no borrowing from neighbours),
        and a small table of the municipalities with their names and check dates.
Only `python build/build_site.py --private` reads it; the public build never does.
Usage (score venv): python pipeline/score/price_join.py
"""
import json, os
from common import ROOT, WORK

PRIVATE = os.path.join(ROOT, 'data', 'private')

def main():
    prices = json.load(open(os.path.join(PRIVATE, 'prices.json'), encoding='utf-8'))
    mu = json.load(open(os.path.join(WORK, 'municipalities.json'), encoding='utf-8'))
    n = len(json.load(open(os.path.join(ROOT, 'data', 'processed', 'score', 'spain.json'), encoding='utf-8'))['bases']['lat'])
    assert len(mu['base_muni']) == n, 'municipalities.json is out of date: rerun municipalities.py'
    munis = {int(k): v for k, v in prices['prices'].items() if v.get('eur_m2')}
    keys = sorted(munis)
    slot = {m: i for i, m in enumerate(keys)}
    out = {'source': prices['source'],
           'munis': [{'name': munis[m]['portal_name'], 'province': munis[m]['portal_province'], 'eur_m2': munis[m]['eur_m2'],
                      'checked': munis[m]['checked']} for m in keys],
           'base_muni': [slot.get(m, -2 if str(m) in prices['prices'] else -1) for m in mu['base_muni']]}   # -2: looked up, too few sales
    json.dump(out, open(os.path.join(PRIVATE, 'score_prices.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f"{len(keys)} municipalities with a price; {sum(s >= 0 for s in out['base_muni']):,} of {n:,} bases priced -> data/private/score_prices.json")

if __name__ == '__main__':
    main()
