# Cycling-base score: Spain prototype plan

Status: **approved 24 October 2026**, with all four decisions in section 7 accepted (cache outside OneDrive, the Python packages, ODbL for the score data, Canaries and Balearics included). Phases 1–3 done (24–25 Oct 2026). **Phase 4 in progress: the weather download runs unattended for about 4 days from 25 Oct 2026** (see "Phase 4" at the end of this file). Phase 5 (the score page, `/score/spain/`) built 25 Oct 2026 with partial weather; owner check-in pending. It implements `docs/cycling-score-spec.md` (decisions of 24 Oct 2026) for Spain, including the Balearics and Canaries.

## 1. What the prototype produces

- Every candidate base gets:
  - **gate pass/fail**: at least 3 paved climbs of ≥ 300 m continuous ascent, dips under 20 m allowed, whose foot is within 26 km by road;
  - the **seven component scores** (climbing, weather, airport, quiet roads, walking, flat/rolling, gravel) and the **weighted total**.
- A **validation table**: known cycling bases must come out near the top, and flat plains must fail the gate.
- A new site page, **`/score/spain/`**:
  - a map of candidate bases coloured by score;
  - weight sliders;
  - a click-through breakdown per base, listing its climbs with distance to the foot, gain and length;
  - later, the score-against-price chart and the price filter.

## 2. Where the work runs, and why it matters

- **Offline, on this machine.** It has 684 GB free, 31 GB of memory and 32 threads. The heavy processing (OpenStreetMap roads, terrain) runs as local scripts. **Only the small results** (a few MB of scores and climbs) are committed. The GitHub Actions build just publishes them, as now.
- **Cache outside OneDrive.** The downloads run to about 5–8 GB: OpenStreetMap Spain is about 1.3 GB, and the terrain tiles are 2–4 GB. If they sat in the project folder, OneDrive would upload all of them. Proposed: `C:\ai-projects\DestinationCyclingCache\` (set by an environment variable, `DC_CACHE`), never synced and never committed.
- **New Python packages,** pinned in `pipeline/score/requirements.txt` and installed **only in a virtual environment inside the cache folder** (`%DC_CACHE%\venv`), never in the global Python. On 24 Oct 2026 a first install into the global Python upgraded numpy and broke another project's package; it was reverted.
  - `osmium` (reads OpenStreetMap files);
  - `rasterio` (terrain tiles);
  - `shapely` and `pyproj` (geometry);
  - `python-igraph` (fast road-network distances).

## 3. Data sources

| Data | Source | Licence / note |
|---|---|---|
| Roads, paths, tracks, peaks, parks | OpenStreetMap extracts from Geofabrik: Spain (1.5 GB, which excludes the Canaries) and the Canary Islands (60 MB, listed under Africa) | ODbL. **Our results are derived from OSM, so the published score data must also be ODbL**, with attribution. This is fine for a free site, but it is a licence condition to accept. |
| Terrain heights | Copernicus DEM GLO-30 (30 m grid; free download from the AWS open-data bucket, no key) | Free with the Copernicus/DLR/Airbus credit line. |
| Countryside quality (for gravel) | ~~CORINE Land Cover 2018~~ **ESA WorldCover 2021** (10 m, AWS open data, no login), since CORINE needs an EU login | CC BY 4.0: "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium". |
| Weather at altitude | Open-Meteo, the existing method (HANDOVER 4.2) | As now. A new batch of points; see the weather phase. |
| Airports with year-round EDI/GLA flights | **Hand-maintained list**, researched and dated, in `config/airports.json` | No open schedule data. Seasonal-only routes count much less in winter (spec). Needs a check by the owner. |
| Property prices | To be researched (phase 6): candidates are Spain's notaries' statistics portal and the Ministry's municipal *valor tasado* | Coverage of small villages is the known gap. |

## 4. Method, in brief

- **Candidate bases.**
  - A 5 km grid over Spain's land: about 20,000 points, of which most will fail the gate.
  - Each point snaps to the nearest paved road, so a point on a mountainside or in the sea is moved or dropped.
  - Named towns are added as extra points for readability.
- **Road network.**
  - Paved roads a cyclist can use: OSM `highway` from `primary` down to `unclassified`, plus residential links.
  - Excluded: motorways and expressways, `access=no`, and unpaved `surface`.
  - Riding distance is a shortest path on this network.
- **Climb finder** (the riskiest part, so it is validated before anything is built on it):
  1. Sample the terrain every 25–30 m along every road.
  2. Find routes on the network that climb ≥ 300 m without any dip of 20 m or more. Each is a climb, with a foot, a top, gain, length and average gradient.
  3. Merge climbs that share most of their road. Count different ascents of the same pass separately (spec default).
  4. **Validate against climbs with well-known figures**: Sa Calobra, Coll de Femenia, Puig Major from Sóller, Coll de Rates, Rocacorba, Els Àngels, and the climbs from the Axarquía coast to Cómpeta. Gain should land within about 10%. If it doesn't, fix the finder before going further.
- **Gate and climbing score.** For each base, the climbs whose foot is within 26 km by road.
  - The gate needs 3 or more.
  - The score rewards the number of climbs, their total and longest gain, and **nearness**: full marks within about 10 km of the base, falling to the 26 km limit.
- **Weather at the climbs.**
  - For bases that pass the gate, rideable days come from Open-Meteo at the **median height of their climbs**. This is the spec's "measured at the climbs, not the house".
  - Months are weighted October–May heavy and summer light.
  - Nearby bases share weather points on a coarser (about 15–25 km) grid, to keep the number of requests reasonable. At the existing rate-limit spacing, that is a few hours of background fetching.
- **Airport access.**
  - Drive time from each base to the nearest listed airport.
  - Uses the road network with typical speeds by road class. It's simpler than full routing software and accurate enough at this scale; it will be checked against known transfer times (e.g. Pollença to Palma airport).
  - The spec's curve: full marks to 60 min, half at 120 min, never zero.
- **Quiet roads, flat/rolling, gravel, walking.** All measured within reach of the base (26 km by road for riding):
  - **Quiet roads:** length and loop-ability of minor paved roads.
  - **Flat/rolling:** low-gradient minor roads.
  - **Gravel:** rideable unpaved tracks (grades 1–3), weighted by countryside quality from CORINE.
  - **Walking:** footpaths and hill paths (`sac_scale`), waymarked hiking routes, peaks, and national or natural parks.
- **Score.** Each component is scaled 0–1 across the Spanish bases that pass the gate, then combined with the agreed weights:
  - climbing 35%, weather 20%, airport 13%, quiet roads 12%, walking 10%, flat/rolling 5%, gravel 5%.
  - The page's sliders change the weights live.

## 5. Phases, each with a check-in

| Phase | Work | Owner check-in |
|---|---|---|
| 1. Foundations | Cache folder, packages, OSM and terrain downloads, road network | None (setup) |
| 2. **Climbs and gate** | Climb finder, validation against the named climbs, gate map of Spain | **Yes: review the climbs found near places you know (Pollença, Girona, Calpe…) before going on** |
| 3. Reach measures | Quiet roads, flat/rolling, gravel, walking, airport times; airport list | Confirm the airport list |
| 4. Weather at altitude | Open-Meteo for gate-passing areas | None |
| 5. Score and page | Combine, validation table, `/score/spain/` with sliders and breakdowns | **Yes: does the ranking look right?** |
| 6. Property prices | Choose and add the source, score-against-price chart, price filter | Confirm the source and its coverage |

Rough effort: phase 2 is the biggest and least certain. Phases 3–5 are each a session or two once the network exists. Phase 6 depends on what the price data turns out to be.

## 6. Risks and limits, stated plainly

- **Terrain on roads:** a 30 m terrain grid gets road gradients slightly wrong in steep, narrow valleys and on bridges and tunnels. Climb gains should be within about 10%; validation will show how close.
- **OSM quality:** OSM's road surface and track tags vary by area, so gravel and "paved" are best-effort. Traffic is approximated by road class only.
- **Airports:** the list is maintained by hand and will go out of date; it carries a date on the page.
- **What it can't judge:** scenery, driver behaviour, road surfaces or cafés. The shortlist still needs local research and visits, as the spec says.
- **Grid points:** a candidate "base" is a grid point, not a property. Prices (phase 6) are at municipality level at best.

## 7. Decisions needed before starting

1. OK to keep a cache of about 5–8 GB at `C:\ai-projects\DestinationCyclingCache\`, outside OneDrive?
2. OK to install the Python packages listed in section 2?
3. OK for the published score data to carry the ODbL licence (it's derived from OpenStreetMap)?
4. Include the Canaries and Balearics from the start? Proposed: yes. Mallorca is the benchmark, and Tenerife and Gran Canaria are on the validation list.

## Phase 1: done (24 October 2026)

- **Cache:** `C:\ai-projects\DestinationCyclingCache\` (env var `DC_CACHE`), outside OneDrive and git. It holds:
  - `venv\` (the score pipeline's own Python environment);
  - `osm\` (Spain 1.4 GB and the Canaries 57 MB, downloaded 24 Oct 2026);
  - `dem\` (127 Copernicus GLO-30 tiles, 3.5 GB; the other 26 one-degree squares in the area are all sea);
  - `work
etwork.npz` (194 MB).
- **Scripts in `pipeline/score/`:**
  - `common.py` (paths, sources);
  - `fetch_inputs.py` (downloads; uses `urllib` because `requests`' own certificate bundle failed on this machine's connection);
  - `build_network.py`;
  - `graph.py` (loads the network as a directed graph, and snaps points onto it);
  - `check_network.py`.
- **Network:** cyclable paved roads (rules in `build_network.py`). 2.9 million junctions, 3.9 million edges, about 494,000 km. It builds in under 2 minutes.
- **Snapping:** about 2% of junctions are one-way stubs you can reach but not leave. Snapping Calpe onto one made it look unreachable, so points now snap only to junctions in a large strongly connected component (≥ 500 junctions, one per island or mainland).
- **Check:** all seven well-known town-to-town riding distances are within 25% of the usual figure, most within 1–2 km:
  - Port de Pollença–Pollença 7.7 km;
  - Palma–Sóller over the col 32.1 km;
  - Girona–Banyoles 18.6 km;
  - Calpe–Altea 11.7 km.
- **Not yet used:** the terrain tiles (phase 2 samples them along every edge's stored road shape).

## Phase 2: climbs and gate (done 25 October 2026)

- **Scripts:**
  - `sample_terrain.py`: heights every ≤ 30 m along every road edge. It uses a 5×5 median filter on the terrain tiles, draws straight lines across bridges and tunnels (about 56,000 and 10,000 edges), and applies a light median-of-3 along roads.
  - `find_climbs.py`, plus the diagnostics `trace_route.py`, `list_climbs.py`, `validate_climbs.py` and `gate.py`.
- **Climb rules:**
  - ≥ 300 m gain;
  - no dip of 20 m below the running high;
  - progress of ≥ 5 m of new height every 1 km;
  - start trimmed to where the road first gains 15 m in 500 m (**3%, confirmed by the owner 25 Oct 2026**);
  - average ≥ 3%;
  - one-way streets respected;
  - up to 3 approaches kept per junction, with feet ≥ 1.5 km apart;
  - upper parts of bigger climbs, and climbs sharing over half their road with a bigger climb ending nearby, dropped.
- **Three fixes found by testing on Mallorca:**
  - climbs now top out partway along an edge (Sa Calobra's top 6.4 km is a single junction-free edge);
  - bridges and tunnels are levelled;
  - the progress rule was relaxed from 10 m per 600 m (it cut Puig Major at the Mirador de Ses Barques) and foot trimming added.
- **Result:** 3,113 climbs across Spain (80 s).
- **Known climbs:**
  - Puig Major from Sóller 875 m / 14.5 km; Coll de Femenia 426 m / 8 km; Coll de Sóller 486 m.
  - Sa Calobra 625 m: about 45 m short, because of a 24 m terrain dip at the "knot", which isn't tagged as a bridge in OSM.
  - Coll de Rates and Rocacorba start lower down than their standard start points.
  - Torrox Costa–Cómpeta splits into several climbs at dips of more than 20 m.
- **Gate:** 25 of 26 named places as expected; all known bases pass and the flat places fail.
  - The exception is the Ebro Delta (Deltebre), which passes with 3 climbs at 23–25 km (the hills behind Tortosa). The nearness scoring in phase 5 will mark it down.
  - Port de Pollença just passes with 3. Sa Calobra and Puig Major start well beyond 26 km by road from there.
- **Owner check-in (25 Oct 2026):**
  - the 3% start rule is kept;
  - the climbs listed near familiar places "sound fine";
  - climbs reached by riding over another climb **count**. They are implemented as *onward* climbs (foot within 26 km of a near climb's top), counted in the score but not the gate. With onward climbs in the gate, Valencia passed; without, the gate is back to 25 of 26 as expected.
  - Port de Pollença: 3 near and 3 onward climbs, including Sa Calobra at 57 km via the Lluc climb. From Pollença, Sa Calobra is 51 km.
- **One unexplained failure:** the first all-Spain run died silently after the search; a rerun completed normally.

## Phase 3: reach measures and airports (25 October 2026, built; airport list to confirm)

- **Airports (`config/airports.json`): a dated DRAFT, from airline announcements and route aggregators.** No official winter 2026/27 timetables were found, and the main route-listing site blocks automated access.
  - Year-round from EDI or GLA as best known: Alicante, Málaga, Tenerife South, Lanzarote, Gran Canaria, Fuerteventura, Barcelona, Madrid.
  - **Palma is "unknown" for EDI in winter, so Mallorca currently has no qualifying airport**, which matters for the benchmark. Girona and Reus are thought to be summer only.
  - **Owner to confirm.** Checked 27 Oct 2026; see "Airport list checked" at the end of this file.
- **Driving network:** `build_network.py --drive` (motorways included, car one-way rules); 537,000 km.
- **Drive times:** `drive_times.py`, with typical speeds per road class and no traffic.
  - Checks: Torrox Costa–Málaga 40 min, Calpe–Alicante 51, Girona–Barcelona 68, Granada–Málaga 78, Puerto de la Cruz–Tenerife South 58.
  - Slightly fast on twisty mountain roads (Ronda–Málaga 74 min, against an estimated 80–100).
  - Two variants are saved: year-round airports only, and including seasonal ones.
- **Off-road features:** `extract_features.py`, from OSM.
  - Gravel tracks 804,000 km; paths 209,000 km; mountain paths 21,000 km; rough tracks 101,000 km.
  - About 270,000 ways in waymarked hiking routes; 82,000 peaks with heights.
- **Measures:** `reach_measures.py`, on 1 km grids with straight-line discs (20 km for roads, 15 km for gravel, walking and peaks).
  - Measures: quiet roads, loop-ability (junctions of three or more minor roads), flat roads (under 2%), gravel weighted by countryside quality, walking (paths, mountain paths ×2, waymarked bonus), peaks.
  - Judgement calls made on 25 Oct 2026, to review with the ranking in phase 5:
    - farmland counts 0.6 for gravel countryside, so tracks through woods and hills count more than vineyard tracks in La Mancha;
    - roads, junctions and paths in built-up land count 0.3.
  - Known limit: dense lowland minor-road networks (e.g. Valencia's huerta) still score highest on quiet roads, because OSM has no traffic data. Phase 5's normalisation must cap each measure.
- **Credits for the score page (phase 5)** must add: Copernicus DEM (DLR/Airbus credit), ESA WorldCover (CC BY 4.0), and OSM (ODbL) for the score data.

## Phase 4: weather at the climbs (IN PROGRESS from 25 October 2026)

- **Candidate bases (`bases.py`):** a 5 km grid over Spain snapped onto the cycling network. 16,609 bases, each with its near and onward climbs; **7,415 (45%) pass the gate** (≥ 3 near climbs). Output `WORK/bases.json`; runs in under a minute.
- **Weather points (`weather_points.py`):** one per 25 km square containing a gate-passing base, at the mean position of those bases. **566 points**, ordered busiest-first (the first 140 cover 3,259 of the 7,415 bases). Portugal added 99 more, and Madeira and Porto Santo use 10 km cells (`docs/portugal-plan.md` section 6): 683 points in all.
- **The download (`weather_fetch.py`):** Open-Meteo daily high, precipitation and max gust, 2017–2025, Europe/Madrid (as HANDOVER 4.1, minus the variables the score doesn't need).
  - **The free tier allows roughly 140 points a day**: each request weighs about 70 "calls" against about 10,000 a day. That is about 2 hours of downloading a day, **about 4 days in all.** The first plan said "a few hours", which was wrong.
  - Every point is saved to `WORK/weather/<id>.json` as it arrives. It resumes after stopping.
  - Progress is in `WORK/weather_status.json` and `WORK/weather_fetch.log`. A lock file stops two copies running at once.
- **Running unattended, set up with the owner on 25 Oct 2026:**
  - **Windows Task Scheduler**, task "Destination Cycling weather fetch":
    - it runs `pipeline/score/run_weather_fetch.cmd` daily at 01:30 and 13:30 and at logon (missed runs start when the PC is next on), each run stopping at the daily allowance;
    - it needs the PC on and the owner logged in to Windows; Claude need not be open;
    - when all points are in, it does nothing.
  - **A Claude scheduled task**, "destination-cycling-weather-check", daily at 09:00 (or when the app next opens):
    - it reads the status file, log and task info, reports progress, flags problems, and **says when the download is complete**;
    - it is read-only, and was saved in Bypass permissions mode (the owner can change that in the app).
- **To check by hand:** read `C:\ai-projects\DestinationCyclingCache\work\weather_status.json`, or count the files in `work\weather`.
- **To restart by hand:** `run_weather_fetch.cmd`, or in a terminal in the repo:
  `$env:DC_CACHE = 'C:\ai-projects\DestinationCyclingCache'; & 'C:\ai-projects\DestinationCyclingCache\venv\Scripts\python.exe' pipeline\score\weather_fetch.py`
  Run only one copy at a time.
- **Scoring (`weather_score.py`, written and tested on early points):**
  - each base uses its own weather point, or borrows the nearest fetched point until its own arrives;
  - temperature is adjusted to the median mid-height of its near climbs at 6.5 °C/km;
  - rideable days per HANDOVER 4.2;
  - the index weights October–May at 1.0 and June–September at 0.25.
  - Output: `WORK/weather_bases.json`.
- **When the download completes:** run `weather_score.py --check`, review the places it prints, record the results here, then disable the Windows task and the daily Claude check (the owner's call).
- **Meanwhile, phase 5 can proceed without the weather.** Build the score page as an explorer (spec section 7a) on bases, climbs, reach measures and drive times, with the weather component filling in from `weather_bases.json` as it becomes available.

## Phase 5: the score page as an explorer (built 25 October 2026; owner check-in pending)

- **New scripts:**
  - `extract_names.py`: OSM towns and villages (8,970) and named passes, saddles and peaks (57,000) → `WORK/names.json`, for labels (8 s).
  - `score_export.py`: precomputes every component (0–1) per base and writes **`data/processed/score/bases.json`** (`spain.json` until Portugal was added; committed, ODbL, 3.9 MB, about 1 MB gzipped). It prints the validation table.
- **`weather_score.py` now scores every base with at least 1 near climb** (10,762), not only the gate-passing 7,415, so the page can relax the gate. Weather for gate-passing bases is unchanged.
- **Page `/score/spain/`, now `/score/bases/`** (`site-src/pages/score.html`, `js/score.js`, `css/score.css`), linked from the landing page as "Prototype". It has:
  - a weight slider, on/off box and "only" button per component;
  - presets: agreed defaults, weather first (20/35/15/12/10/4/4), climbing only;
  - flights mode: year-round only, seasonal at half credit, ignored;
  - the gate as a switch, with 1–8 near climbs;
  - a canvas map of all 10,762 bases;
  - top 25 (optionally one per 15 km);
  - the known-places table;
  - a per-base breakdown with each component's points, rideable days by month, and near and onward climbs (named from the nearest OSM pass or peak, linked to OSM).
  - Settings are remembered in the browser only. Credits added: OSM (ODbL), Copernicus DEM, ESA WorldCover, Open-Meteo, the airport list's date.
- **Component formulas (judgement calls, for the owner to review):**
  - **Climbing is absolute, not percentile-scaled.** Each climb is worth min(gain, 1,500) / 300, times nearness (1 to 10 km, 0.4 at 26, 0.1 from 60). The score is 0.8 × (1 − e^(−sum/5)) + 0.2 × the best near climb (300 m → 0, 1,000 m → 1).
    - The first try scaled linearly to the 95th percentile (28 near climbs), and Pollença scored 0.10.
  - Weather, quiet roads (0.6 km + 0.4 junctions), walking (0.75 paths + 0.25 peaks), flat and gravel are each scaled between their 5th and 95th percentile over gate-passing bases.
  - Airport uses the spec's curve on drive minutes, in the page.
  - Onward climbs are capped at the 12 most valuable per base.
- **Validation, default weights, weather from 141 of 566 points (rank among 7,415 gate-passing bases):**

  | Place | Year-round flights | Seasonal at half |
  |---|---|---|
  | Granada | 1 | 1 |
  | Gran Canaria (San Bartolomé) | 210 | 210 |
  | Alicante | 239 | 239 |
  | Girona | 505 | 505 |
  | Tenerife (Puerto de la Cruz) | 550 | 550 |
  | Altea / Calpe / Cómpeta | 606 / 655 / 625 | about the same |
  | Nerja / Torrox / Ronda / Olot | 1,034 / 1,280 / 1,328 / 1,108 | about the same |
  | Sóller | 1,497 | 942 |
  | Palma | 2,158 | 1,465 |
  | Pollença / Port de Pollença | 4,371 / 6,078 | 3,355 / 5,195 |
  | Jaca | 5,595 | 5,598 |
  | Deltebre (Ebro Delta, should fail) | passes the gate, about 4,500 | |

- **What looks wrong, for the check-in:**
  - **Mallorca's north is low.** The causes, in order:
    1. the year-round airport rule (Palma at the 0.15 floor costs about 11 points);
    2. half the 15–20 km discs is sea, so quiet roads, walking and gravel come out low on every coast;
    3. Pollença has only 4 near climbs.
  - **Barcelona's suburbs rank high** (Pallejà 7th, Santa Coloma de Gramenet, Llinars). The reasons are a 14-minute airport, dense minor roads (OSM has no traffic) and Collserola and Montserrat climbs.
  - Granada leads on sheer number of climbs plus walking.
  - Possible fixes to discuss:
    - scale the reach measures per km² of land rather than per disc;
    - penalise built-up land more for quiet roads;
    - decide whether the seasonal mode should be the default.
  - **Nothing has been tuned to the list yet.** The owner decides.
- **When the weather completes:** rerun `weather_score.py`, then `score_export.py`, then rebuild. The weather normalisation and the ranks will shift.
- **Done 30 October 2026:** all 566 points fetched and the steps above run, with no change of method or weights. 9,653 of 10,762 bases have their own point; the rest use the nearest. The default list now opens with Callosa d'en Sarrià, Cenes de la Vega, Arona, Agost and Arucas. The owner's review of the new ranking is still to come (DC-18).

### Phase 5 revision (owner, 25 October 2026): reach measures per km² of land, built-up roads penalised more

- **Owner's view:** agreed that Mallorca's north scoring low and Barcelona's suburbs ranking high both look wrong.
- **`reach_measures.py` changes:**
  - Minor roads and junctions in built-up land now count **0.1** (was 0.3), for quiet roads only. Flat roads keep 0.3.
  - Land area within 15 and 20 km is recorded (`land15`, `land20`). Usable land is WorldCover land (not water, sea or no-data) within 3 km of a Spanish network junction. The second condition is needed because Portugal, France and Andorra aren't in the OSM extract, so would count as empty land.
  - Checks: Port de Pollença 34% land, Pollença 47%, Calpe 53%, Madrid 98%, Badajoz 69% (Portugal left out).
- **`score_export.py` change:** quiet roads, junctions, flat, gravel, walking and peaks are now per km² of land: raw ÷ max(land, 25% of the circle) × circle. The page shows the land % in the breakdown.
- **Validation after the change (rank of 7,415, default weights):**

  | Place | Year-round flights | Seasonal at half |
  |---|---|---|
  | Granada | 7 | 7 |
  | Alicante | 125 | 125 |
  | Tenerife (Puerto de la Cruz) | 128 | 128 |
  | Calpe | 196 | 196 |
  | Altea | 241 | 241 |
  | Torrox / Nerja | 347 / 345 | about the same |
  | Dénia | 395 | 395 |
  | Gran Canaria (San Bartolomé) | 425 | 425 |
  | Cómpeta | 480 | 480 |
  | Sóller | 759 | 418 |
  | Girona | 807 | 815 |
  | Olot | 1,217 | 1,240 |
  | Ronda | 1,393 | 1,418 |
  | Palma | 1,781 | 1,109 |
  | Pollença / Port de Pollença | 3,166 / 3,979 | 2,208 / 2,929 |
  | Jaca | 5,710 | 5,710 |
  | Deltebre (should fail) | about 3,700 | |

- **Barcelona's suburbs dropped** (Pallejà 7 → 111, Llinars 62 → 135). But some built-up places still lead: Torrequebrada (Benalmádena) is 1st, Esplugues de Llobregat 15th, Santa Coloma de Gramenet 41st.
  - They are carried by climbing, weather and an airport 10–20 minutes away. None of those is a reach measure.
  - The score has no measure of **how built-up the base itself is** (riding out through a city every day).
  - Candidate fix, not yet built: a penalty or filter on the built-up share within about 5 km of the base.
- **Pollença still ranks about 3,000.** Its climbing is 0.43 (4 near climbs, the nearest about 10 km away) against 0.8–1.0 for the Costa Blanca, the Axarquía and the Canaries.

### Phase 5 revision 2 (owner, 25 October 2026): built-up base penalty

- **The measure:** the share of usable land within 5 km of the base that ESA WorldCover maps as built-up (`reach_measures.py`: `built5`, `land5`).
  - Across gate-passing bases: median 0.8%, 90th percentile 8%, 99th 34%.
  - Examples: Pollença 0–5%, Sóller 2%, Nerja 9–12%, Calpe 28–41%, Alicante 34%, Granada 37%, Torrequebrada 38%, Esplugues de Llobregat 59%.
- **The penalty** (`score_export.py`, `c_built`): 0 up to 10% built-up, rising linearly to 1 at 50%.
  - The page multiplies the total by (1 − strength × penalty).
  - Strength defaults to **20%**; it is adjustable 0–50% and can be switched off. The presets don't change it.
  - **Default on, confirmed by the owner on 27 Oct 2026.**
- **Validation (rank of 7,415, default weights, penalty at 20%):**

  | Place | Year-round flights | Seasonal at half | No penalty |
  |---|---|---|---|
  | Nerja | 265 | 265 | 345 |
  | Tenerife (Puerto de la Cruz) | 272 | 272 | 128 |
  | Altea | 292 | 292 | 241 |
  | Gran Canaria (San Bartolomé) | 304 | 305 | 425 |
  | Cómpeta | 356 | 359 | 480 |
  | Marbella | 403 | 407 | 474 |
  | Granada | 409 | 413 | 7 |
  | Torrox | 501 | 505 | 347 |
  | Calpe | 504 | 509 | 196 |
  | Dénia | 561 | 567 | 395 |
  | Alicante | 599 | 605 | 125 |
  | Sóller | 665 | 299 | 759 |
  | Olot / Girona | 1,134 / 1,137 | 1,151 / 1,154 | 1,217 / 807 |
  | Ronda | 1,333 | 1,353 | 1,393 |
  | Pollença / Port de Pollença | 3,133 / 3,950 | 2,167 / 2,897 | 3,166 / 3,979 |
  | Palma (city) | 4,278 | 3,411 | 1,781 |
  | Jaca | 5,702 | 5,702 | 5,710 |

- **Top 15 (one per 15 km), with the penalty:**
  - Cenes de la Vega (by Granada, at the foot of the Sierra Nevada), Mijas, Agost, Totana;
  - Bajamar and San Andrés (Tenerife);
  - Nerja;
  - Valsequillo and Santa María de Guía (Gran Canaria);
  - Vélez de Benaudalla;
  - Argentona (Maresme);
  - Jete, El Bebedero, Las Rosas, el Ràfol d'Almúnia.
  - All are under 10% built-up.
- **Barcelona's suburbs:** Esplugues and Santa Coloma drop out of the top 1,000. Pallejà is 446th; Llinars del Vallès (10% built-up) stays 91st.

### Airport list checked (27 October 2026)

- **Owner's answers:**
  - Both Edinburgh and Glasgow count; the routes are similar and the choice is by flight times on the day.
  - Trips range from a few days at short notice to a couple of months.
  - So "year-round" means direct flights every month from November to March, at least about twice a week.
- **Method (Claude, at the owner's request):**
  1. Read the Edinburgh and Glasgow "Airlines and destinations" tables on Wikipedia.
  2. Ran Google Flights direct-only searches for Wednesday 13 January and Wednesday 10 February 2027. Where there is no flight that day, these show the nearest days that have one.
  - The frequencies are estimates from those searches, not timetables.
- **Changes in `config/airports.json`:**
  - **Now year-round:** Seville (EDI, about twice a week: Mon and Sat) and **Santander** (new; EDI, about twice a week: Sun and Thu). Both are at the threshold.
  - **Confirmed year-round:**
    - Madrid and Barcelona from EDI, about 3–4 days a week; neither from GLA in winter;
    - Alicante, Málaga, Tenerife South, Lanzarote, Gran Canaria and Fuerteventura, from both.
  - **Confirmed seasonal:** Valencia, Girona, Reus, Palma, Ibiza, Menorca, and **Bilbao**. Wikipedia lists Vueling as year-round to Bilbao, but no flights were found on or near either date.
  - **Murcia:** no flights at all.
- **Effect (default weights, penalty 20%):**
  - The top 15 is unchanged.
  - The north coast rises sharply: Potes (Picos de Europa) 4,975 → 3,104, Cangas de Onís 3,816 → 2,205, Santander city 5,823 → 4,243.
  - Aracena 6,482 → 5,120; Grazalema 1,288 → 1,233.
  - Mallorca slips as others pass it: Pollença 3,133 → 3,526, Palma 4,278 → 4,629.
  - 3,579 bases have a different nearest year-round airport.
- **Re-check each autumn:** winter schedules change, and Seville and Santander sit at the twice-a-week threshold.

## Phase 6: property prices (started 27 October 2026; private)

Decided with the owner: prices from the notaries' portal, for **private family use only**. They are never committed or published; the public page is unchanged. Source, method, scripts, guards and the first lookups (156 municipalities, 735 bases) are in `docs/price-data-plan.md` section 4. To view the private copy locally:

- `python build/build_site.py --private`
- `node tests/serve.js _site 8000`
- open http://127.0.0.1:8000/score/bases/

Rebuild without `--private` before anything else uses `_site`. Next: the login-protected family copy (Cloudflare Pages + Access), once the weather is complete and the ranking is checked.

### Owner check-in on the ranking (27 October 2026)

- The owner looked over the live score page and found that **it looks good**.
- So the weights, the gate (3 near climbs), the built-up penalty (on at 20%) and the year-round flights rule all stay as they are.
- Once the full weather is in, the ranking gets only a brief recheck; ranks will shift a little.

### What kind of property (owner, 27 October 2026)

- The owner would consider:
  - a house or flat in a small town or village;
  - something just outside a small town or village;
  - a house on its own in the country, outside a larger town, as long as facilities aren't too far away.
- The owner leans towards **rural**. It depends on the property and its surroundings.
- **How this fits the score:**
  - The built-up penalty already favours villages and the countryside over towns and resort strips, so nothing changes now.
  - The score doesn't yet measure "not too far from facilities". A possible later factor is the drive to the nearest town with everyday shops and a health centre, from OSM.
  - The €/m² figure is a municipal average that mixes town flats and country houses, so for a rural house it's only a broad guide.

### Order of work (owner, 27 October 2026)

1. Get everything working first: the full weather rerun and the price refresh.
2. Then make the interface as clear and intuitive as possible (DC-27).
3. Then open the login-protected family copy. The Cloudflare key, account and sign-in list are ready, so this step is only the setup.
4. Only then add new factors. "Near facilities" waits until this point.
