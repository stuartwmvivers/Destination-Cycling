# Destination-Cycling — project handover

Handover from a Claude.ai session (16–22 October 2026) to Claude Code. It records what exists, how every number was made, what was decided and why, and where the project is meant to go. Read it fully before changing data or method: the site's value depends on the numbers being reproducible and honestly caveated.

> **This repository is public.** Keep personal matters (finances, property plans, family details, home address) out of every file, commit message and issue. Place names on the site are fine; who lives where is not.

---

## 1. What this project is

A free, static website that helps a keen road cyclist (the owner, based in Scotland) find **places to buy a holiday home to use as a cycling base**. It started as a question about the Costa Brava's recorded weather and grew into a comparison tool.

**The site's single job:** let someone compare candidate places by how much good riding they offer through the year, against a familiar UK baseline, and see how far to trust the figures.

**Long-term aspiration** (see section 9): cover Spain, Portugal, France, the UK and later Italy, Croatia and Slovenia, and rank places not just on climate but on **climbing terrain, quiet roads and airport access**: a "cycling base score".

**Audience:** the owner and family (one son in Bristol uses it to compare against his own weather); publicly viewable but not marketed.

---

## 2. Current state (22 October 2026)

| Item | State |
|---|---|
| Live site | https://stuartwmvivers.github.io/Destination-Cycling/ (landing page) and `/spain-coast/` (Spain dashboard). The old `/spanish-coast-climate.html` redirects to `/spain-coast/`. |
| Repo | `stuartwmvivers/Destination-Cycling`, public. GitHub Pages is deployed by GitHub Actions (`.github/workflows/deploy.yml`) on every push to `main`: build, `data_check.py`, `render_check.js`, then publish `_site/`. A failed check publishes nothing. |
| Site root (`/Destination-Cycling/`) | Landing page `index.html` (added 23 Oct 2026). |
| Built files | Not committed since refactor phase D (23 Oct 2026). The last self-contained single-file page is in git history: `git show 052c30e:spanish-coast-climate.html`. |
| Source | `config/`, `data/processed/`, `site-src/` and `build/build_site.py` build `_site/`. The new Spain dashboard renders identically to the published page across 31 settings (`tests/compare_pages.js`, 23 Oct 2026). |
| Private twin | A Claude.ai "Dashboard" artifact with the same page and data. **Not reachable from Claude Code**; treat this repo as canonical from now on. |
| Pushing | Since 23 Oct 2026 the project is a local git clone in the owner's folder, and the owner pushes from there. Claude Code's push permission is not granted, so ask the owner to push. |

### What the page shows

- **Controls:** place, compare-with, month slider (Jan–Dec + "Whole year"), year slider (2017–2025 or "All", the 9-year average), Play (steps months), and a measure picker (9 measures, section 4.3).
- **Takeaway line**, then **headline tiles** for the selected place and period, with the comparison place underneath.
- **Map card** (since refactor phase B, 24 Oct 2026): a zoomable Leaflet map on OpenStreetMap tiles, with tabs *All Spain*, *Costa Brava*, *Costa del Sol*, *Costa Blanca*, *Mallorca* that move the view. It follows the selected place's region unless a tab is clicked. Dots are coloured by the chosen measure; clicking one selects that place. Labels show for every place once zoomed in to a region (a label that would overlap another is hidden), otherwise only for the selected and compared places. A strip under the map shows the colour scale and the UK baselines (Dunning, Bristol) on the same scale.
- **Through the year:** monthly line (temperatures, with a min–max band across years) or bars (day counts), with the comparison place in grey.
- **Every month, every year:** a 9×12 heatmap plus whole-year column and average row. Clicking a cell sets the month and year.
- **Year by year:** bars for the chosen month across 2017–2025 with an average line and comparison marks.
- **Modelled vs measured:** for the 17 towns with a paired weather station, a model-vs-station table for all measures and a monthly chart, with source credit and coverage caveats (section 5).
- **All places table:** sortable, filterable by region, highlights the selected and compared places.
- **Method notes**, and a footer with attributions.

---

## 3. Repository layout (this bundle)

```
CLAUDE.md                     short orientation for Claude Code (points here)
HANDOVER.md                   this file
docs/cycling-score-spec.md    the agreed design for the future cycling-base score
docs/refactor-plan.md         the multi-region refactor (phases A-D; A and D done 23 Oct 2026)
config/places.json            every place (id, name, country, region, lat/lon, model elevation, setting, note, baseline)
config/regions.json           one entry per dashboard page: countries, baselines, defaults, map tabs, landing card, prose, credits (see 7.1)
config/sources.json           station data sources: credit line shown under each station comparison
data/processed/climate/<country>.json    modelled monthly rows (4.2), one file per country (ES, GB)
data/processed/stations/<country>.json   station monthly rows (5.3)
data/reference/aemet-station-inventory.json   AEMET station list (public, reusable)
data/raw/, data/interim/      git-ignored download caches and intermediates
pipeline/openmeteo_fetch.py   modelled data: fetch + aggregate (Python port, see 4.1); --check compares without writing
pipeline/openmeteo_browser_reference.js   the exact JS aggregation originally used
pipeline/meteocat_fetch.py / meteocat_aggregate.py   Catalan stations (needs METEOCAT_API_KEY)
pipeline/aemet_fetch.py / aemet_aggregate.py         Spanish national stations (needs AEMET_API_KEY)
pipeline/midas_fetch.py / midas_aggregate.py         UK baseline stations, Met Office MIDAS Open (needs CEDA_ACCESS_TOKEN)
pipeline/score/               cycling-base score pipeline (docs/score-prototype-plan.md): own venv and large inputs in DC_CACHE, outside OneDrive and git
pipeline/stations_combine.py  merges station sets -> data/processed/stations/<country>.json (rebuilds only sources whose inputs are present)
site-src/pages/               index.html (landing), region.html (dashboard template, one page per region), about.html (method, trust, sources)
site-src/css/                 tokens.css (light + dark design tokens), dashboard.css, landing.css
site-src/js/                  dash-shim.js (the `dash` API, fetches region data), periods.js (calcs), dashboard.js (UI)
build/build_site.py           -> _site/: pages, columnar data files per region, summary.json, vendored d3
_site/                        git-ignored build output
tests/data_check.py           4.4 reference values + region files match data/processed
tests/render_check.js         Playwright smoke test over HTTP (desktop light + phone dark, overflow, errors, failed requests)
tests/compare_pages.js        before/after markup comparison of a dashboard across 31 settings
tests/serve.js                tiny static server for tests and local preview
.github/workflows/deploy.yml  build + checks + publish to GitHub Pages on push to main
.env.example                  key names; real keys go in git-ignored .env
```

Build and test:
```bash
npm ci && npx playwright install chromium
python3 build/build_site.py
python3 tests/data_check.py
node tests/render_check.js _site
node tests/serve.js _site 8000      # preview; pages fetch data, so file:// won't work
```

---

## 4. Modelled climate data — method (must stay consistent)

### 4.1 Source and fetch

- **Open-Meteo Historical Weather API** (`archive-api.open-meteo.com/v1/archive`), default model selection, free tier, **CC BY 4.0** (attribute "Open-Meteo"). Open-Meteo's terms make the free API non-commercial.
- Daily variables: `temperature_2m_max, temperature_2m_min, precipitation_sum, wind_gusts_10m_max, wind_direction_10m_dominant`. Gusts are in km/h.
- Period **2017-01-01 to 2025-12-31** (9 years, 108 months). 2016 was dropped: the session found a coarser grid behind that year, which blurred neighbouring towns together. Re-verify this against Open-Meteo's model documentation before extending backwards.
- **`timezone=Europe/Madrid` for every place, including the UK ones.** Keep it, or re-fetch everything.
- Open-Meteo returns the nearest grid cell and adjusts temperature to the requested point's elevation. The `elevation_m` in `places.json` is the elevation Open-Meteo used.
- Original fetch: browser JavaScript, 16–17 Oct 2026, because the Claude.ai workspace couldn't reach the API at first. `pipeline/openmeteo_fetch.py` is a faithful port. Its aggregation was **verified identical to the JS on synthetic data**, including JS-style half-up rounding (`jsround`), and it was **checked against the live API on 23 Oct 2026** for Begur, Torrox Costa and Dunning: `tmax`, `tmin`, `hot`, `frost` and `tram` match the committed rows exactly in all 108 months. The rain-based measures (`rain`, `wet`, `ride`, `warm`) differ in a minority of months by 1–2 days or a few mm, spread across all years. That points to Open-Meteo having revised its precipitation since the original fetch (not confirmed). Effect on 9-year averages is small (rideable days a year: Begur 190.8 → 191.1, Torrox 294.4 → 295.2, Dunning 91.9 → 92.0), but **a re-fetch no longer reproduces the committed rows exactly**. So: use `python3 pipeline/openmeteo_fetch.py --check <place_id>` to compare without writing; treat the committed file as a snapshot; and if new places are added, re-fetch every place in the same run so all places come from the same data version (then update the reference values in 4.4 and say so).
- Rate limit: about 5 heavy requests in a row triggered HTTP 429 ("Minutely API request limit exceeded"). The script waits 10 s between places and 65 s after a 429.

### 4.2 Aggregation (per place, per month)

| Field | Definition |
|---|---|
| `tmax`, `tmin` | mean of daily max / min, °C, rounded to 0.1 (half-up) |
| `rain` | sum of daily precipitation, mm, rounded to integer |
| `wet` | days with precipitation ≥ 1 mm |
| `ride` ("rideable day") | tmax ≥ 11 °C **and** precipitation < 1 mm **and** max gust < 50 km/h |
| `warm` ("warm riding day") | 14 ≤ tmax ≤ 30 °C, plus the same dry and calm conditions |
| `hot` | tmax ≥ 30 °C |
| `frost` | tmin ≤ 0 °C |
| `tram` ("north-wind day") | max gust ≥ 50 km/h **and** dominant direction ≥ 290° or ≤ 40° (N/NW) |

`tram` captures the Tramuntana (Costa Brava, Mallorca) but **not** the Levante (easterly, Strait of Gibraltar / Estepona). Any strong-wind day still counts against `ride`.

Row schema, `data/processed/climate/<country>.json` (2,376 rows in all = 22 places × 108 months):
`{place, year, month, tmax, tmin, rain, wet, ride, warm, hot, frost, tram}`

The page derives whole-year values (temperatures = mean of 12 monthly means; counts and rain = sums) and 9-year averages with min/max across years, in the `periods` calc in `site-src/js/periods.js`. `build/build_site.py` repeats the 9-year averages (same rounding) in `_site/data/summary.json` for the landing page and future ranking.

### 4.3 The places

| id | Name | Region | Requested lat, lon | Model elev m | Note |
|---|---|---|---|---|---|
| begur | Begur | Costa Brava | 41.954, 3.207 | 200 | Hilltop village; seafront ≈1 °C warmer |
| llanca | Llançà | Costa Brava | 42.36, 3.15 | 25 | Tramuntana corridor |
| roses | Roses | Costa Brava | 42.262, 3.176 | 11 | Bay of Roses |
| lescala | L'Escala | Costa Brava | 42.124, 3.131 | 31 | Central coast |
| palamos | Palamós | Costa Brava | 41.846, 3.129 | 12 | Southern-central coast |
| tossa | Tossa de Mar | Costa Brava | 41.72, 2.93 | 12 | South coast |
| figueres | Figueres | Costa Brava | 42.267, 2.961 | 47 | Empordà plain |
| girona | Girona | Costa Brava | 41.98, 2.82 | 79 | City |
| olot | Olot | Costa Brava | 42.18, 2.49 | 440 | Volcanic hills |
| nerja | Nerja | Costa del Sol | 36.746, −3.876 | 31 | Axarquía coast |
| torrox | Torrox Costa | Costa del Sol | 36.728, −3.955 | 14 | West of Nerja |
| frigiliana | Frigiliana | Costa del Sol | 36.791, −3.896 | 321 | **Shares Nerja's grid cell**: temperature height-adjusted, rain/wind identical |
| marbella | Marbella | Costa del Sol | 36.51, −4.885 | 31 | |
| estepona | Estepona | Costa del Sol | 36.426, −5.146 | 20 | Levante-exposed |
| alicante | Alicante | Costa Blanca | 38.345, −0.481 | 19 | City |
| altea | Altea | Costa Blanca | 38.599, −0.051 | 59 | |
| javea | Xàbia (Jávea) | Costa Blanca | 38.789, 0.166 | 35 | |
| palma | Palma | Mallorca | 39.57, 2.65 | 28 | City |
| soller | Sóller | Mallorca | 39.766, 2.715 | 39 | Steep valley the grid can't resolve; rough guide only |
| pollensa | Pollença | Mallorca | 39.877, 3.016 | 55 | Mallorca's cycling hub |
| dunning | Dunning | UK | 56.31, −3.58 | 97 | UK baseline (Perthshire) |
| bristol | Bristol | UK | 51.4545, −2.5879 | 11 | UK baseline (south-west England) |

Excluded on purpose: **Cadaqués**, which falls in the same grid cell as Roses.

### 4.4 Reference values for sanity checks

9-year averages from the committed data. If a rebuild changes these, something in the method changed.

| Place | Jan high / low °C | Jan rideable days | Rideable days a year | Days ≥ 30 °C a year |
|---|---|---|---|---|
| Begur | 12.0 / 4.4 | 12.4 | 190.8 | 17.6 |
| Torrox Costa | 16.9 / 9.8 | 24.0 | 294.4 | 57.4 |
| Nerja | 16.8 / 10.0 | 22.6 | 278.4 | 70.4 |
| Alicante | 16.6 / 8.3 | 23.6 | 263.1 | 38.0 |
| Palma | 14.8 / 8.0 | 19.0 | 244.9 | 71.8 |
| Pollença | 14.0 / 8.8 | 13.8 | 212.3 | 23.7 |
| Dunning | 5.6 / 0.8 | 0.0 | 91.9 | 0 |
| Bristol | 7.4 / 2.1 | 0.1 | 118.2 | 1.2 |

Bristol's hot days were listed as 0 in the original handover; the committed data has always given 1.2 (11 days ≥ 30 °C over 2017–2025, e.g. July 2022). Corrected 23 Oct 2026; no data or method changed. `tests/data_check.py` checks this table against the built site.

---

## 5. Weather-station validation

### 5.1 Why

Reanalysis models smooth reality over grid cells. To know how far to trust the modelled numbers, each candidate town is paired with the nearest suitable real station, and the **same nine measures** are computed from the station's daily data over the same months.

### 5.2 Stations used

**Meteocat** (Servei Meteorològic de Catalunya, XEMA network), API `api.meteo.cat`, daily statistics variables 1001 TX, 1002 TN, 1300 PPT, 1512/1515 gust and direction at 10 m (or 1514/1517 at 2 m):

| Town | Station (code) | km | Station elev m | Wind |
|---|---|---|---|---|
| Begur | Torroella de Montgrí (UE) | 8.7 | 4 | none |
| Roses | Roses (D4) | 1.1 | 23 | 10 m |
| L'Escala | Sant Pere Pescador (U2) | 6.5 | 3 | 10 m |
| Palamós | Castell d'Aro (DO) | 9.0 | 14 | 10 m |
| Figueres | Castelló d'Empúries (W1) | 10.8 | 5 | none |
| Girona | Girona (XJ) | 1.2 | 72 | 10 m |
| Olot | Olot (YB) | 1.8 | 435 | 10 m |

There are no stations for **Llançà** (nearest is a 198 m mountain pass, unrepresentative) or **Tossa** (nearest working station is 13 km away and already used for Palamós). Lloret de Mar (CF) and the old Olot site (DC) are closed. In Meteocat metadata, `estats[].codi == 2` with `dataFi == null` means operational.

**AEMET** OpenData, `opendata.aemet.es`, daily climatological values (max 6-month window per request; a two-step response where the first call returns a `datos` URL):

| Town | Station (indicativo) | km | Station elev m | Coverage 2017–25 |
|---|---|---|---|---|
| Nerja | Nerja (6213X) | 3.3 | 169 | ~99% |
| Torrox Costa | Torrox (6205X) | 0.3 | 3 | **~50%** |
| Marbella | Marbella Puerto (6076X) | 6.7 | 2 | ~94% |
| Estepona | Estepona (6058I) | 1.3 | 19 | ~87% |
| Alicante | Alicante city (8025) | 3.3 | 81 | 100% |
| Altea | Benidorm (8036Y) | 9.7 | 36 | **~80%** |
| Xàbia | Xàbia (8050X) | 0.5 | 15 | ~93% |
| Palma | Palma Puerto (B228) | 2.8 | 3 | 100% |
| Sóller | Port de Sóller (B051A) | 3.8 | 5 | **~60%** |
| Pollença | Pollença (B760X) | 0.7 | 45 | ~96% |

Frigiliana has no station of its own (it shares Nerja's).

**Met Office MIDAS Open** (via CEDA, `dap.ceda.ac.uk`, dataset version 202607; added 24 Oct 2026) for the UK baselines. No station near either town has temperature, rain and wind for 2017–2025, so each baseline **pairs** a synoptic station (temperature and gusts) with a nearby rain gauge:

| Baseline | Temperature + wind (src_id) | km, m | Rain gauge (src_id) | km, m | Coverage 2017–25 |
|---|---|---|---|---|---|
| Dunning | Strathallan Airfield (00212) | 9.3, 35 | Kinkell Bridge No 2 (55762, gauge id 881658) | 9.3, 19 | ~98% |
| Bristol | Almondsbury (62122) | 10.9, 75 | Clifton, Oakfield Road (09621) | 1.6, 61 | temperature and wind 2018–2025 only (**~80%**) |

The Dunning station itself (00216) has no data after 2016. Filton stops in 2018; Long Ashton and Bristol Weather Centre have nothing recent.

### 5.3 Station aggregation rules

- Meteocat: a day counts only if its `percentatge` ≥ 80. A measure is valid for a month only if ≥ 90% of days are present. Gusts are m/s × 3.6 → km/h. The **direction used is the direction of the maximum gust**, not the dominant direction as in the model, a known asymmetry for `tram`.
- AEMET: decimal commas, `prec` "Ip" (trace) = 0.05 mm, "Acum" ignored, `racha` m/s × 3.6, `dir` in tens of degrees (99 = variable, never counts as north). Precipitation is the 07–07 day. The same 90% monthly completeness rule applies.
- `ride` and `warm` need temperature, rain and gust all present, so stations without wind have no rideable-day figures.
- Station scripts use Python's `round()` (banker's rounding). The committed station data was made that way, so that's the reference.
- MIDAS (`midas_aggregate.py`), with the same 90% rule and thresholds:
  - **Temperature:** the daily max is the 12-hour reading ending 21:00 UTC (09–21) and the min the one ending 09:00 (21–09); rare 24-hour readings fill gaps.
  - **Rain:** 09–09 UTC totals, credited to the day the period **starts**. MIDAS `ob_date` is the end date; checked against modelled Dunning rain, r 0.61 shifted vs 0.53 unshifted. Multi-day totals are ignored. Kinkell Bridge has two gauges, and the one with most daily records (881658, 96% passing QC) is used.
  - **Gusts:** hourly max gusts in knots × 1.852; a day's gust is the highest of its UTC hours (needs ≥ 19 of 24) and its direction is that gust's, as for Meteocat.
  - **Paired stations:** `ride` and `warm` combine one station's temperature and gusts with the other's rain on the same day. Rows carry `rain_station`, `rain_station_name`, `rain_distance_km` and `rain_elevation_m`, and the page names both stations.

Row schema, `data/processed/stations/<country>.json` (1,836 rows):
`{place, source: "Meteocat"|"AEMET", station, station_name, distance_km, elevation_m, gust_height_m|null, year, month, tmax, tmin, rain, wet, ride, warm, hot, frost, tram}`, with `null` where a measure isn't valid for that month.

### 5.4 Findings (the most important result so far)

Yearly averages over matched months, station vs model.

| Station (town) | High: st − model | Low: st − model | Wet days st/model | Rideable days st/model | ≥ 30 °C days st/model |
|---|---|---|---|---|---|
| Roses | +2.0 | −1.4 | 54/76 | 236/160 | 63/23 |
| Sant Pere P. (L'Escala) | +1.0 | −3.5 | 53/80 | 278/188 | 40/29 |
| Castell d'Aro (Palamós) | +1.9 | −2.4 | 54/85 | 285/208 | 39/12 |
| Girona | +1.6 | −3.2 | 62/93 | 294/213 | 77/58 |
| Olot | +1.6 | −2.0 | 78/113 | 271/213 | 61/40 |
| Torroella (Begur)* | +2.2 | −1.8 | 53/86 | — | 43/18 |
| Castelló (Figueres) | +0.1 | −1.4 | 51/91 | — | 46/63 |
| Nerja | −0.3 | −1.0 | 41/59 | 309/278 | 38/68 |
| Torrox (partial) | −0.4 | −1.4 | 25/41 | 296/304 | 41/72 |
| Marbella Puerto | −0.7 | −0.2 | 37/53 | 287/278 | 8/40 |
| Estepona | +1.3 | −0.3 | 40/61 | 281/214 | 61/46 |
| Alicante | +1.5 | −1.3 | 34/49 | 317/263 | 77/38 |
| Benidorm (Altea) | +1.9 | −1.4 | 34/55 | 315/277 | 78/34 |
| Xàbia | +2.0 | −1.6 | 41/60 | 287/253 | 84/44 |
| Palma Puerto | +0.5 | +1.2 | 52/84 | 300/245 | 62/72 |
| Port de Sóller (partial) | −0.6 | +0.2 | 49/102 | 272/205 | 39/77 |
| Pollença | +3.3 | −2.2 | 66/92 | 274/214 | 84/25 |
| Strathallan + Kinkell Br. (Dunning) | +1.0 | +0.2 | 152/171 | 114/91 | 0/0 |
| Almondsbury + Clifton (Bristol, partial) | +0.8 | −0.1 | 139/162 | 150/116 | 3/1 |

\*Begur's model point is ~200 m higher than Torroella, which explains ≈1.3 °C of its gap.

Conclusions:
1. **Everywhere, the model overcounts wet days** (by ~30–70% in Spain, ~12–14% at the UK baselines), so **real rideable days are equal to or higher than modelled, never lower**. The model's absolute numbers are pessimistic, and that holds for the UK baselines too (Dunning 114 real vs 91 modelled rideable days a year, Bristol 150 vs 116), so Spain-vs-UK comparisons aren't skewed by the baselines being treated differently.
2. **Temperature bias is regional, not uniform.** Costa Brava, Costa Blanca and Pollença: the model is 1.5–3 °C too cool by day and too warm by night. Costa del Sol: about right by day, but it **overstates summer heat** (sea breeze; e.g. Marbella 8 real ≥ 30 °C days a year vs 40 modelled). Coastal Mallorca: close, with the gain coming from fewer wet days.
3. Rankings between places probably hold, but **a single correction factor is wrong**. One derived from Catalonia would wrongly heat the Costa del Sol.

**Decision (owner, 20–21 Oct 2026, "option 3"):** show model and station side by side now; **do not** apply any correction until it has been validated region by region (ECA&D / AEMET / MIDAS). If a corrected layer is added later, it must be per-region, labelled as adjusted, and switchable off.

---

## 6. Data sources, access and licence obligations

| Source | Use | Access status (22 Oct 2026) | Licence / obligations |
|---|---|---|---|
| Open-Meteo | Modelled climate for all places | No key needed. Host `archive-api.open-meteo.com` | CC BY 4.0, attribute Open-Meteo. Free tier is non-commercial. |
| Meteocat XEMA API | Catalan stations | Owner holds a key (personal citizen plan). Quota 20,000 XEMA calls/month; ~3,300 used on 20 Oct 2026. Host `api.meteo.cat`, header `X-Api-Key` | API terms: personal use, no redistribution, attribute, notify Meteocat of publications. **Written permission (21 Oct 2026) to publish monthly summaries on this site** with attribution. **Never publish or commit raw daily Meteocat data.** Credit: "Servei Meteorològic de Catalunya (Meteocat), used with permission". |
| AEMET OpenData | Spanish national stations | Owner holds a key (JWT, **expires ~29 Jan 2027**; the owner must re-request at opendata.aemet.es). Header `api_key` | Reuse authorised citing AEMET: "© AEMET, Agencia Estatal de Meteorología". |
| ECA&D (KNMI) | Planned: station validation across Europe | No registration for station data. `www.ecad.eu` was allowlisted, but the site returned **HTTP 503** on 21 Oct 2026. Retry. Bulk files may be served from another host. | Non-commercial research and education only. Acknowledge data providers; cite Klein Tank et al. (2002), *Int. J. Climatol.* 22, 1441–1453. |
| Met Office MIDAS Open (via CEDA) | UK baseline stations (Dunning, Bristol), since 24 Oct 2026 | The owner has a CEDA account. Scripted downloads need a short-lived **access token** in `CEDA_ACCESS_TOKEN` (in the git-ignored `.env`); directory listings are public. Host `dap.ceda.ac.uk`, dataset version 202607 (daily temperature, daily rain, hourly mean wind). | Open Government Licence v3. Credited on the page, footer and About page. Before any formal publication, add the dataset DOIs from the CEDA catalogue for version 202607 (not yet recorded here). |
| OpenStreetMap tiles (`tile.openstreetmap.org`) | Map background, via Leaflet 1.9.4 (vendored) | No key. The [tile usage policy](https://operations.osmfoundation.org/policies/tiles/) allows light use like this site with visible attribution; no bulk or automated downloading (the tests serve blank tiles instead). If traffic grows, switch to a tile provider: change the URL in `initMap` in `site-src/js/dashboard.js`. | Data © OpenStreetMap contributors, ODbL; attribution shown on the map and in the footer. Leaflet is BSD-2. (The geo-maps / Natural Earth / es-atlas outlines used until 24 Oct 2026 are gone.) |

**Secrets:** keys go in environment variables (`METEOCAT_API_KEY`, `AEMET_API_KEY`, `CEDA_ACCESS_TOKEN`) or a git-ignored `.env`. Never in code, commits, the built page or issues. **Ask the owner for keys; they're not in this repo.**

**Network:** a sandboxed Claude environment may need these hosts allowlisted: `archive-api.open-meteo.com`, `api.meteo.cat`, `opendata.aemet.es`, `www.ecad.eu`, `dap.ceda.ac.uk`, plus npm/PyPI.

---

## 7. Front-end architecture (current)

- **Since refactor phase A (23 Oct 2026)** the dashboard is split into `site-src/pages/region.html` (markup), `site-src/css/dashboard.css` and three scripts loaded in order after d3:
  1. `site-src/js/dash-shim.js` implements the `dash` API (`data`, `onData`, `calc`, `params`, `setParams`, `resetParams`, `colors`, `setLink`), which comes from the Claude.ai Dashboard artifact the page was first built in. It fetches `data/regions/<region>.json`, named by `window.DC_PAGE`, expands the columns back into the original row shape, persists params to localStorage (`dc-params-<region>`), caches calcs and redraws on resize. It reports `loading` until the data arrive and `error` if the fetch fails.
  2. `site-src/js/periods.js`: `dash.calc('periods', …)` builds per place × year × period rows (period `'1'`…`'12'` or `'year'`; year `'2017'`…`'2025'` or `'all'`), with `_lo`/`_hi` for the all-years rows; `dash.calc('station_periods', …)` does the same for stations, plus `_n` counts of years with data.
  3. `site-src/js/dashboard.js`: the UI IIFE, whose `dash.onData(…)` redraws everything from `dash.params()`.
- **Region file** (`_site/data/regions/<region>.json`, ~120 KB for Spain): `{id, name, years, places, climate: {place: {measure: [108 values]}}, stations: {place: {source, station, …, series: {measure: [108, null where invalid]}}}, outlines}`. Months run year-major from January of the first year. It holds the region's places plus the UK baselines.
- **Params:** `place` (default `begur`), `compare` (`dunning`), `measure` (`tmax`), `year` (`all`), `period` (`'1'`), `frame` (`auto` | `spain` | `brava` | `sol` | `blanca` | `mallorca`), `region` (`all` | region name).
- **Map:** Leaflet 1.9.4 with OpenStreetMap raster tiles, built once by `initMap` in `dashboard.js`; each redraw restyles the circle markers and updates the key strip (`#cb-mapkey`). A frame (`P.frame`, or the selected place's region) is fitted to that region's places, only when the frame changes, so changing measure doesn't undo panning. Region moves aren't animated: restyling markers during Leaflet's zoom animation left their paths blank. Dark mode inverts the tiles with a CSS filter. Scroll-wheel zoom is off (page scrolling stays normal) and one-finger dragging is off on touch devices (pinch zooms). Markers are keyboard-focusable (Enter selects).
- Styling: CSS custom properties (`--cds-*`, `--color-*`, `--font-anthropic-*`) from `site-src/css/tokens.css`, with light and dark themes. Charts are d3 v7. The layout works at 400 px with no horizontal scroll, and the smoke test checks this.
- **Region settings** (since phase C): `build_site.py` writes each region's settings into `window.DC_PAGE` (years, defaults, overview and tabs, place groups, north-wind note, station source credits) and fills the template's `{{…}}` prose placeholders from `config/regions.json`. Baselines are the places with `baseline: true`. Nothing Spain-specific is left in `site-src/js/` or `region.html`.

### 7.1 Adding a region (since refactor phase C, 24 Oct 2026)

No page code changes are needed:

1. **Places:** add them to `config/places.json` with `place` (id), `name`, `country` (ISO code; data files are per country), `region` (the sub-region shown in groups and filters), `lat`, `lon`, `elevation_m`, `note`.
2. **Region:** add an entry to `config/regions.json`. It needs:
   - `id` (the URL: `/<id>/`), `name`, `title`, `description` and `countries`;
   - `baselines` (place ids, normally `["dunning", "bristol"]`), `default_place` and `default_compare`;
   - `overview` (`{id, label}` for the all-places map view) and `tabs` (`[{id, label, region}]`, one map tab per sub-region; any other region falls back to the overview);
   - `card` (`{title, text, link}`, the landing-page card; `text` may use `{places}`, `{years}` and `{stations}`);
   - `tram_note` (optional local name for north winds);
   - `station_summary`, `method_places`, `method_measures` (region prose on the dashboard) and `credits` (footer HTML).
3. **Modelled data:** fetch it. `openmeteo_fetch.py` re-fetches **every** place in one run (HANDOVER 4.1), then check the 4.4 reference values and say if they moved.
4. **Stations:** optional. Run the station scripts and add any new station source to `config/sources.json`.
5. **Build and check:** `build_site.py`, `data_check.py` and `render_check.js _site`.

The build fails on any `{{PLACEHOLDER}}` left unfilled, so a missing prose field can't reach a page. This was checked with a made-up second region in a scratch clone on 24 Oct 2026: the page, tabs, groups, defaults, baselines, prose and landing card all came from config.

---

## 8. Decisions log

| Date | Decision | Why |
|---|---|---|
| 16 Oct | Use modelled reanalysis (Open-Meteo) as the backbone | Only source consistent across every place and country; complete, no gaps |
| 16 Oct | Drop 2016; use 2017–2025 | Coarser grid for 2016 blurred towns together |
| 16 Oct | "Rideable day" = ≥ 11 °C high, < 1 mm rain, < 50 km/h gusts | Simple, explainable, cycling-relevant. The 14–30 °C "warm" variant was added for comfort |
| 17 Oct | Publish a standalone single file on GitHub Pages; keep the Claude version private | Public access without a Claude account; offline-capable |
| 17 Oct | Add Bristol as a second UK baseline; drop "(home)" labels | Family member in Bristol compares his own weather; no personal labelling on a public page |
| 20 Oct | **No database for now**; static files | Data small (~14 KB/place), changes yearly, read-only; static hosting is simpler and free. Revisit if: user-written data (favourites, notes), daily-level queries over thousands of places, or live/forecast data. (A Supabase connector exists on the owner's account if that day comes.) |
| 20 Oct | **Architecture must change before multi-country expansion** | The hand-built maps and single inlined file won't scale (9.1) |
| 20–21 Oct | Station validation shown side by side; no correction yet ("option 3") | Bias is regional; a Catalan correction would mislead elsewhere |
| 21 Oct | Meteocat monthly summaries published with permission; AEMET published with credit | Licence compliance |
| 22 Oct | Future ranking = cycling-base score with **climbing as the dominant factor**, gated | Owner's stated priorities (docs/cycling-score-spec.md) |
| 23 Oct | Refactor plan approved (docs/refactor-plan.md): **drop the offline single file** (pages fetch data), **deploy with GitHub Actions** (built files no longer committed), region URLs like `/spain-coast/`, **one dashboard page per country** with sub-region map shortcuts; keep the `dash` API | Scale to many regions without page surgery; reverses the 17 Oct offline decision |

---

## 9. Roadmap and aspirations

### 9.0 Quick wins
- **Root landing page** (`index.html`) introducing Destination-Cycling and linking to the Spain dashboard, ready for more regions. Keep the existing URL working.
- Update README with what the site is, sources and credits, and how to build.
- Commit this repo structure (the owner currently has only the built file and a two-line README in the repo).

### 9.1 Architecture refactor (before adding countries) — done 23–24 Oct 2026
All four phases are done; see `docs/refactor-plan.md` and section 7.1 for adding a region. The original aims, kept for reference:
- **Build pipeline:** `pipeline/` scripts → `data/processed/` → site. Adding a region should mean adding rows to a places config and re-running, with no page surgery.
- **Per-country (or per-region) data files** loaded on demand, plus a small **summary file** (place × month aggregates for every place) for search and ranking. Keep it static; GitHub Pages is fine at this scale.
- ~~**Replace the hand-built SVG maps with a zoomable slippy map**~~ Done 24 Oct 2026 (Leaflet + OpenStreetMap tiles; see section 7).
- Decide whether to keep the `dash`-style API (proven, small) or refactor to plain ES modules. Either is fine; keep the smoke test green.
- Consider multiple HTML pages (landing, region dashboards, method/about) rather than one huge page.

### 9.2 Station validation everywhere
- **AEMET:** more stations across all Spanish candidate areas (the inventory is in `data/reference/`).
- **ECA&D:** daily station series for Portugal, France, Italy, Croatia, Slovenia and the UK. Same measures, same completeness rules.
- ~~**MIDAS Open:** Bristol and Dunning stations~~ Done 24 Oct 2026 (5.2).
- Output a **per-region model-bias table**. Only then consider an optional, clearly labelled, per-region adjusted layer (section 5.4 decision).

### 9.3 Cycling-base score
The big aspiration: rank places as **holiday-home cycling bases**, not just climates. The full agreed design is in **`docs/cycling-score-spec.md`**. In short (weights as rebalanced on 24 Oct 2026): climbing (gated, 35%), weather (20%, weighted to autumn–spring and **measured at the climbs' altitude**), airport access with **year-round direct flights from Edinburgh/Glasgow** (13%, soft decay, never zero), quiet roads (12%), walking (10%), a flat/rolling option (5%) and gravel (5%, a bonus). Validate that it ranks Mallorca, Girona, Calpe and similar near the top before trusting new suggestions. **Prototype for Spain first.**

Decisions of 24 Oct 2026 (spec section 8): the **climbing gate** is at least 3 paved climbs of ≥ 300 m continuous ascent whose foot is within 26 km by road (ideally about 10 km, as Port de Pollença to the Coll de Femenia); **airports** are Edinburgh and Glasgow only; **gravel** is a bonus valued for pleasant countryside, not climbs (its own small component); **walking** is secondary but important (10%); a dip of under 20 m doesn't break a climb; **property prices** are a big factor, shown as a separate axis next to the score with a price filter, not blended in.

### 9.4 Coverage expansion
Order agreed in principle: all of Spain (including the Canaries) → Portugal → France → UK → Italy, Croatia, Slovenia. Candidate areas the owner and Claude expect to score well, as hypotheses for the score to test: Axarquía hinterland (behind Nerja/Torrox), inland Costa Blanca (Calpe/Dénia/Coll de Rates), Gran Canaria and Tenerife, Algarve hinterland (Monchique), Ronda/Grazalema, Eastern Pyrenees/Roussillon (winter-at-altitude will penalise these). **Mallorca is the benchmark**: terrain and weather are ideal, but prices are out of reach, so a place scoring close to Mallorca at a lower price is the goal.

### 9.5 Later ideas
- Sea temperature (Copernicus Marine), which matters for shoulder-season comfort.
- Winter daylight hours (a big difference between Scotland and Andalucía, and it limits ride length).
- Year-round direct-flight data from EDI/GLA (also used by the score).
- Property price signals (patchy per country; keep separate from the climate score).
- Refresh each January to add the latest year (append-only; re-run pipeline and build).

---

## 10. Owner's priorities and working preferences

- **Riding priorities:** climbs matter most ("I'd rather have Scottish weather with quiet hills than a better climate with only flat busy roads"), with some flat or rolling roads for variety. The home terrain is hilly with little flat. Mountains are a big draw. Walking is the other main pastime; gravel is a bonus (nice countryside, no climbs needed), secondary to road riding; property prices are a big factor.
- **Access:** wants to fly out at short notice for a few days to a week. Airport transfer ideally under 2 hours, preferably less; longer is tolerable if price, weather and riding are excellent. **It's a balance, not a hard cut-off.**
- **Communication:** direct and candid; flag weaknesses and uncertainty plainly; no flattery. They test claims, so state where numbers come from and what hasn't been verified. British English.
- **Publishing:** the repo and site are public. Confirm licence terms before publishing any new data source; credit every source on the page; keep personal information out.
- **Process:** verify outputs (rebuild, smoke test, look at the page) before handing over; keep the reference values in 4.4 stable unless the method deliberately changes, and say so if it does.

---

## 11. Known issues and caveats

- Model limitations: diurnal range is smoothed (days too cool, nights too warm in many regions), and wet days are overcounted. All absolute figures are pessimistic; see 5.4.
- Begur's model point is the hilltop at ~200 m; the seafront is warmer.
- Nerja and Frigiliana share rain and wind; Cadaqués is omitted (same cell as Roses).
- Sóller's terrain is unresolved by the model; treat its figures as indicative only.
- `tram` misses the Levante; the station gust direction differs in definition from the model's dominant direction.
- Partial station records: Torrox ~50%, Port de Sóller ~60%, Benidorm ~80%, Bristol ~80% (flagged on the page when below 85%).
- The UK baselines' station figures come from paired stations ~9–11 km from the towns (Bristol's temperature from Almondsbury, north of the city), and MIDAS days run 09–09 UTC rather than midnight to midnight.
- The heatmap is dense at phone width but usable. On the map, labels in tight clusters (Nerja / Frigiliana / Torrox) hide each other until you zoom in.
- A fresh Open-Meteo fetch differs slightly from the committed rain-based figures (see 4.1); the committed data is a 16–17 Oct 2026 snapshot.

---

## 12. First tasks for Claude Code

1. Read `CLAUDE.md`, this file and `docs/cycling-score-spec.md`. Run `npm ci`, build, and the smoke test, and confirm the output matches the committed `spanish-coast-climate.html`.
2. ~~Verify `pipeline/openmeteo_fetch.py` against the live API for one place.~~ Done 23 Oct 2026 (see 4.1).
3. Add the root landing page and README update (9.0). Ask the owner before pushing.
4. Propose the 9.1 refactor as a short plan (layout, data splitting, map library) **before** implementing. The owner likes to see the approach first.
5. Retry ECA&D. When the CEDA token arrives, add MIDAS stations for Bristol and Dunning.
6. Then start the Spain prototype of the cycling-base score.
