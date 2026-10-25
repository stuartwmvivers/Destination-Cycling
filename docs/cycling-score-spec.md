# Cycling-base score — design spec (agreed 22 October 2026; decisions updated 24 October 2026)

Goal: rank locations as **holiday-home bases for road cycling (above all climbing) and walking**, across Spain, Portugal, France and the UK at first, then further afield. The score screens a whole country down to a shortlist. It can't judge scenery, road surfaces, driver behaviour or café culture, so a shortlist still needs local research and a visit.

## 1. Owner's priorities (in their words, paraphrased)

- Climbs are the most important thing. Mountains are a big draw. Some flat or rolling roads are nice for variety, but not essential.
- Would rather have poor weather with quiet hills than a better climate with only flat, busy roads.
- Short-notice trips of a few days to a week: airport transfer ideally under 2 hours, preferably less. Longer isn't ruled out if price, weather and riding are excellent. **It's a balance.**
- Mallorca is the ideal for terrain and weather, but too expensive. The aim is "close to Mallorca, at a better price".
- Walking is the other main pastime, so good walking country within reach matters too (added 24 Oct 2026).
- Gravel matters, but it is secondary to good road riding.
- Property prices are a big factor in the final choice.

## 2. Unit of analysis

A regular grid, each cell treated as a possible home location. Start at roughly 10 km spacing for the coarse screen, but compute the climbing gate on a finer grid (about 5 km or less) or for named towns: the ideal ride to the first climb is only about 10 km, so a 10 km cell is too coarse to place a base. Named towns are overlaid for readability. Precompute everything offline; the site reads a small results file.

## 3. Components and weights (rebalanced 24 Oct 2026 to add walking and gravel; adjustable in the UI)

| Component | Weight | Measure | Notes |
|---|---|---|---|
| **Climbing** | 35% + gate | From a DEM (Copernicus GLO-30 or SRTM) along paved roads: the climbs whose **foot** is within **26 km riding distance (by road)** of the base; their number, total gain and longest climb. Named passes from OSM (`mountain_pass=yes`, `natural=saddle` with `ele`) as a bonus and sanity check. | **Gate (agreed 24 Oct 2026): at least 3 paved climbs of ≥ 300 m continuous ascent whose foot is within 26 km by road**, or the cell is excluded however good its weather. 26 km is about an hour's easy riding on the flat, the owner's absolute maximum to reach the climbs. **Within the score, nearer is better**: full marks when the climbs start within about 10 km (the benchmark is Port de Pollença to the foot of the Coll de Femenia), falling towards 26 km. Check the gate passes Pollença, Girona, Calpe/Dénia, the Axarquía and the Dunning baseline, and fails flat plains such as the Ebro Delta and La Mancha. |
| **Weather** | 20% | Rideable days (definition in HANDOVER 4.2), weighted to the months the home would be used: about Oct–May heavy, summer light. | **Measured at the climbs, not the house:** sample the climate data at the elevation of the area's climbs (Open-Meteo adjusts temperature to the requested elevation; snow and cold matter). A sunny valley with snow-shut cols in February must not score as Mallorca does. Apply the regional station-bias findings once validated (HANDOVER 5.4), labelled. |
| **Quiet roads** | 12% | OSM within reach: length and connectivity of paved minor roads (`unclassified`, `tertiary`, quieter `secondary`; exclude motorways and trunk roads); loop-ability (graph cycles) rather than out-and-backs. | OSM has no traffic volumes; road class is a proxy. Later refinement: national traffic counts (Spain, UK DfT, France) where available. Gravel is scored separately (below). |
| **Airport access** | 13% | Drive time to the nearest airport **with year-round direct flights from Edinburgh or Glasgow** (agreed 24 Oct 2026: these two only) (OurAirports + routing, e.g. OSRM on OSM). | Score curve: 1.0 up to 60 min, falling to ~0.5 at 120 min, then slowly towards a floor (~0.15), **never 0**. Seasonal routes count much less in winter. Flight-schedule data is patchy; start with a hand-maintained list of year-round routes and document its date. |
| **Flat / rolling option** | 5% | Length of low-gradient minor roads within reach | For recovery days. |
| **Gravel (bonus)** | 5% | OSM rideable unpaved tracks within reach (`highway=track` grades 1–3, `surface` = gravel, compacted, fine_gravel, dirt), with connectivity for loops, weighted by **countryside quality**: forest, natural and protected areas, open farmland; not urban or industrial land (land cover from CORINE / OSM `landuse`). | Agreed 24 Oct 2026: gravel is a **bonus**, secondary to road riding. It needs **no climbs** to be good, just pleasant countryside, so it is independent of the climbing gate and measure. |
| **Walking** | 10% | OSM footpaths and hill-walking routes within reach (`highway=path`/`footway`, `sac_scale`, waymarked hiking `route=hiking` relations), plus nearness to mountains and national or natural parks. | Agreed 24 Oct 2026: **secondary but important**. Not a deal breaker, but good walking within reach makes a place more attractive. It will correlate with climbing (good climbs and good walking usually go together), so in practice it mostly separates places that are otherwise similar, which is the intent. |

Weights total 100%. Climbing stays dominant (35% plus the gate); the others were scaled down from the 22 Oct draft (40/25/15/15/5) to make room for walking (10%) and gravel (5%). The score uses an additive weighted sum of 0–1 normalised components, after the climbing gate, so one weak factor costs points without eliminating a place (the balance requirement).

**Property prices** (a big factor; **agreed 24 Oct 2026: a separate axis shown next to the score, with a price filter**), not blended into it, because price data vary in quality by country and the real question is two-dimensional ("close to Mallorca, at a better price"). The UI plots score against typical price and has a price filter. No blended ranking for now. **The filter's range is set by the user on the page and remembered only in their browser.** No budget figure is stored in this public repo; the page default is wide. The price source per country is still to choose (patchy by country; keep the source and date on the page).

## 4. Validation before trusting new suggestions

Known good cycling bases must rank near the top of their country: e.g. **Mallorca (Pollença / Sóller area), Girona, Calpe/Dénia, Tenerife and Gran Canaria, the Algarve hinterland, Provence/Mont Ventoux, the Pyrenees (summer), the Peak District / Yorkshire Dales (UK)**. If they don't, fix the weights or measures, not the list. Flat agricultural plains and busy coastal strips should score low. Record the validation results in the repo.

## 5. Useful supporting signals (validation, not scoring)

- Pro-team winter training bases (small hand-maintained list).
- Grand Tour and major sportive routes.
- Bike shops (`shop=bicycle` in OSM), cycling-friendly hotels.
- The owner's own Strava history. A Strava connection exists in the owner's Claude account; use it for calibration only and never publish it.
- **Do not scrape the Strava heatmap**: its terms forbid it, and Strava Metro is only for planners.

## 6. Data volume and where to compute

- OSM extracts (Geofabrik) for four countries run to several GB, and processing them is heavy. Do it as an offline build (locally or in CI) and commit only the small results (scores per grid cell + top-N shortlist).
- DEM tiles: download per country and cache outside git.

## 7. Phasing

1. **Spain prototype:** climbing + quiet roads + airport access + existing climate method, on a ~10 km grid; validation table (section 4); a simple map layer on the site.
2. Weather-at-altitude refinement and the per-region station bias (once validated).
3. Portugal, France, UK; then Italy, Croatia, Slovenia.
4. UI: adjustable weights, a "find places like Mallorca" similarity view, and shortlists.

## 7a. Exploring, not a fixed ranking (owner, 25 Oct 2026)

The page is a tool for exploring candidates, not a single verdict. Every component is precomputed per base; the score is worked out live in the page from the user's choices:
- a weight slider per component (climbing, weather, airport, quiet roads, walking, flat/rolling, gravel), each of which can also be switched off;
- **flights mode:**
  - year-round direct only (the strict rule);
  - seasonal direct counted at reduced credit (e.g. Palma, which is seasonal for the owner; connecting flights out of season are acceptable but not ideal);
  - flights ignored;
- **the climbing gate as a switch**, with the minimum number of near climbs adjustable, to see what a relaxed gate opens up;
- "rank by one thing" shortcuts and presets: the agreed defaults (section 3), "weather first" and "climbing only";
- a per-base breakdown showing why it ranks where it does;
- the price filter (phase 6).

The owner's general view: weather should lead, and destinations reachable direct and year-round from Edinburgh have an advantage. The default weights stay as agreed in section 3; "weather first" is offered as a preset.

## 8. Decisions and open questions

Decided (owner, 24 Oct 2026):
- **Climbing gate:** at least 3 paved climbs of ≥ 300 m continuous ascent whose foot is within 26 km by road (about an hour's easy riding); nearer is better, ideally about 10 km.
- **Airports:** year-round direct flights from Edinburgh or Glasgow only.
- **Gravel:** a bonus, secondary to road riding; valued for pleasant countryside, not climbs (its own small component).
- **Property prices:** a big factor, shown as a separate axis next to the score with a price filter, not blended in (section 3).
- **Walking:** secondary but important, 10% (section 3). The other weights were rebalanced: climbing 35%, weather 20%, airport 13%, quiet roads 12%, flat/rolling 5%, gravel 5%.
- **Continuous ascent:** a dip of under 20 m of descent does not break a climb.
- **Climbs reached over another climb (25 Oct 2026): they count.** An *onward* climb is one whose foot is within 26 km by road of the top of a near climb, e.g. Sa Calobra from Pollença, over the Lluc climb. Onward climbs count in the climbing score, rated by their longer distance (base to the first foot, plus the first climb, plus the ride on), but **not towards the gate**. Counted in the gate they let flat places pass on hills beyond the hills: Valencia passed with 1 near and 3 onward climbs.
- **Where a climb starts (25 Oct 2026):** where the road first gains at least 15 m in 500 m (3%). Gentle lower slopes don't count as part of the climb, e.g. the approach from Pollença towards the Coll de Femenia. The same rule means Els Àngels from the Girona side (about 1–2% in its lower half) falls under 300 m and doesn't count, while Els Àngels from the east does.

Open:
- Property prices: which price source per country (and at what level: municipality, province or region).
- Whether different ascents of the same pass (e.g. both sides of the Coll de Femenia) count as separate climbs. Default: yes.
