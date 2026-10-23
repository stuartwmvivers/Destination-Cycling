# Cycling-base score — design spec (agreed 22 October 2026)

Goal: rank locations as **holiday-home bases for a road cyclist who loves climbing**, across Spain, Portugal, France and the UK at first, then further afield. The score screens a whole country down to a shortlist. It can't judge scenery, road surfaces, driver behaviour or café culture, so a shortlist still needs local research and a visit.

## 1. Owner's priorities (in their words, paraphrased)

- Climbs are the most important thing. Mountains are a big draw. Some flat or rolling roads are nice for variety, but not essential.
- Would rather have poor weather with quiet hills than a better climate with only flat, busy roads.
- Short-notice trips of a few days to a week: airport transfer ideally under 2 hours, preferably less. Longer isn't ruled out if price, weather and riding are excellent. **It's a balance.**
- Mallorca is the ideal for terrain and weather, but too expensive. The aim is "close to Mallorca, at a better price".

## 2. Unit of analysis

A regular grid (start with roughly 10 km spacing over the target country), each cell treated as a possible home location. Named towns are overlaid for readability. Precompute everything offline; the site reads a small results file.

## 3. Components and weights (initial; adjustable in the UI)

| Component | Weight | Measure | Notes |
|---|---|---|---|
| **Climbing** | ~40% + gate | From a DEM (Copernicus GLO-30 or SRTM) along the road network within ~40 km riding distance: number of climbs with ≥ 300 m gain, total climbable gain, longest climb. Named passes from OSM (`mountain_pass=yes`, `natural=saddle` with `ele`) as a bonus and sanity check. | **Gate:** below a minimum climbing threshold, the cell is excluded however good its weather. This matches the "hills over climate" preference. Tune the threshold so the Scottish home area passes and the flat plains fail. |
| **Weather** | ~25% | Rideable days (definition in HANDOVER 4.2), weighted to the months the home would be used: about Oct–May heavy, summer light. | **Measured at the climbs, not the house:** sample the climate data at the elevation of the area's climbs (Open-Meteo adjusts temperature to the requested elevation; snow and cold matter). A sunny valley with snow-shut cols in February must not score as Mallorca does. Apply the regional station-bias findings once validated (HANDOVER 5.4), labelled. |
| **Quiet roads** | ~15% | OSM within reach: length and connectivity of paved minor roads (`unclassified`, `tertiary`, quieter `secondary`; exclude motorways and trunk roads); loop-ability (graph cycles) rather than out-and-backs. | OSM has no traffic volumes; road class is a proxy. Later refinement: national traffic counts (Spain, UK DfT, France) where available. Optional gravel layer (`highway=track` + `surface`). |
| **Airport access** | ~15% | Drive time to the nearest airport **with year-round direct flights from Edinburgh or Glasgow** (OurAirports + routing, e.g. OSRM on OSM). | Score curve: 1.0 up to 60 min, falling to ~0.5 at 120 min, then slowly towards a floor (~0.15), **never 0**. Seasonal routes count much less in winter. Flight-schedule data is patchy; start with a hand-maintained list of year-round routes and document its date. |
| **Flat / rolling option** | ~5% | Length of low-gradient minor roads within reach | For recovery days. |

The score uses an additive weighted sum of 0–1 normalised components, after the climbing gate, so one weak factor costs points without eliminating a place (the balance requirement).

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

## 8. Open questions for the owner

- Minimum climbing threshold. Suggest calibrating so that the home area in Perthshire passes.
- Which UK departure airports count (EDI, GLA, also ABZ/PIK?).
- Whether gravel matters at all.
- Whether property-price signals should be shown alongside (kept separate from the score).
