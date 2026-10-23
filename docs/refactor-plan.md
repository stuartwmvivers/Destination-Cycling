# Refactor plan: from one Spain page to a multi-region site

Status: **approved 23 October 2026** as written (drop offline, deploy with Actions, `/spain-coast/` URLs, one page per country). **Phases A and D done 23 Oct 2026** (see the end of this file, D was brought forward); B and C to do.

Goal (HANDOVER 9.1): adding a region should mean adding places to a config file and re-running the pipeline and build, with no edits to page code. The numbers on the page must not change as a side effect: the reference values in HANDOVER 4.4 are the test.

## 1. What blocks expansion today

| Problem | Where | Effect |
|---|---|---|
| Hand-drawn map, one pre-projected frame per region, hand-tuned label offsets | `FRAMES`, `FRAME_LABELS`, `LABEL_SIDE`, `REGION_TAGS` in `src/dashboard.html`; `map-outlines-spain.json`; `pipeline/maps/mk*.js` | Every new region needs outlines built by hand and label nudging. The legacy scripts need a 117 MB npm package and intermediate files that no longer exist. |
| Region list, years and defaults hard-coded in page code | `REGIONS`, `REGION_FRAME`, `YEARS`, `DEFAULTS`, year slider `min="2016"`, "2017–2025" strings | New regions or a new year (the January refresh) need code edits. |
| Spain-specific prose in the page | Title, station summary, method notes, Tramuntana definition, footer ("Snapshot built 17 October") | Wrong or misleading once other regions exist. |
| Everything inlined into one HTML file | `build/build_standalone.py` | Fine at 1.2 MB, but every region's data would load on every page. |
| One data file per source for all places | `climate-spain-2017-2025.json`, `stations-all-…json` | Re-fetching one region rewrites a shared file; naming is Spain-specific. |

Data size is a smaller problem than the handover assumed. In row-per-month JSON, one place is about 14 KB. Stored as columns (one array per measure), it's about **3 KB, or roughly 1 KB gzipped**. So even 500 named places across Europe would be about 1.5 MB raw. Splitting the data is worth doing for tidiness, not because size forces it.

## 2. Proposed structure

```
config/
  regions.json          id, name, country, map centre/zoom, default place, compare place, notes
  places.json           every place (adds country + region id to today's fields)
pipeline/               unchanged role; outputs per-country files
data/processed/
  climate/<country>.json        monthly rows, same schema as today
  stations/<country>.json       same schema as today
site-src/               (today's src/, reorganised)
  pages/index.html, pages/region.html, pages/about.html
  js/dash-shim.js, js/periods.js, js/dashboard.js, js/map.js
  css/tokens.css, css/dashboard.css
build/build_site.py     -> _site/ (not committed; deployed by GitHub Actions)
_site/                  (git-ignored build output)
  index.html
  spain-coast/index.html          one page per region, generated from region.html
  about/index.html                method, station findings, sources and licences
  data/summary.json               every place: 9-year monthly averages, for the landing page and ranking
  data/regions/spain-coast.json   that region's places, monthly series and stations, columnar
  vendor/d3-7.9.0.min.js, vendor/leaflet-1.9.4/…
  spanish-coast-climate.html      small redirect to /spain-coast/ so the old link keeps working
```

### Decisions inside this, with my recommendation

1. **Pages: one template, one generated page per region.** Each region gets a real URL (`/spain-coast/`), its own title and description, and loads only its own data file. The same JS runs every region. The UK baselines are included in every region file so "compare with Dunning/Bristol" works everywhere. Comparing a place against one in another region loads that region's file on demand.
2. **Data loaded with `fetch` instead of inlined.**
   - *Cost:* the "works offline as a single file" property goes, and opening a built page straight from disk (`file://`) stops working, so local previews need `python -m http.server`.
   - *Gain:* pages stay small, and adding a region doesn't slow the others.
   - The 17 October decision chose offline-capable. **This reverses it, so it needs your OK.**
3. **Map: Leaflet 1.9.4 with OpenStreetMap raster tiles.**
   - Places become circle markers coloured by the chosen measure, and the region tabs become "fly to" buttons. The UK-baselines box stays as an overlay.
   - Leaflet is small (~40 KB), stable and needs no key. The OSM tile policy allows a low-traffic, non-commercial site like this, with attribution and no bulk downloading.
   - Dark mode uses a CSS filter on the tiles, or a dark tile provider (CARTO and Stadia both offer one; their free-tier terms need checking before we use them).
   - The future score grid (~5,000 cells for Spain at 10 km) renders fine with Leaflet's canvas renderer.
   - *Alternative:* MapLibre GL with free vector tiles (OpenFreeMap). It looks sharper and has proper dark styles, but it's ~800 KB of JS. Not worth it yet.
   - This change deletes `map-outlines-spain.json`, `pipeline/maps/` and about 200 lines of map code.
4. **Keep the `dash` API; split the code into files.** The shim is 50 lines and the page logic is proven. Rewriting it as modules would be a big change with no visible benefit and a real risk of changing numbers. Instead:
   - the shim gains an async `load()` that fetches the region file and then fires `onData`;
   - the big script becomes a few plain files (`periods.js` for the calcs, `dashboard.js` for the UI, `map.js`);
   - the hard-coded region and year constants are read from the data file instead.
   - There's still no bundler or framework; the build just copies and templates files.
5. **Deploy with GitHub Actions; stop committing built files.**
   - The workflow builds `_site/` on every push to `main` and publishes it, using GitHub's official Pages actions. Source and output stop being mixed at the repo root, and a stale or hand-edited built file can't be served.
   - *Cost:* you change one setting (Settings → Pages → Source: GitHub Actions), and a failed build means no deploy (the old site stays up).
   - *Alternative:* keep committing built files at the root, as now. Simpler, but it gets messy with many pages.

## 3. How we prove nothing changed

- **Number check (new, `tests/data_check.py`):** recompute the HANDOVER 4.4 reference values from the *site* data files and fail if any differ. This guards the method through every refactor step.
- **Before/after page comparison (one-off):** for several places, months and years, read the headline tiles and table text from the current page and from the refactored page, and require them to be identical.
- **Smoke test:** extended to every generated page; it serves `_site/` over a local HTTP server instead of `file://`. The same rules apply: no page errors and no horizontal overflow at 400 px.

## 4. Phases (each one ends with everything green and the site deployable)

| Phase | Work | Visible change |
|---|---|---|
| A. Data and build | `config/`, per-country processed files, columnar region files plus `summary.json`, `build_site.py`, fetch-based shim, number check, before/after comparison | None: same Spain page, new plumbing |
| B. Map | Leaflet map replaces the SVG map; delete outlines and legacy scripts | New zoomable map |
| C. Generalise | Region and year constants from data; Spain prose moved into region config or the About page; About page; redirect for the old URL | URL becomes `/spain-coast/` (old one redirects) |
| D. Deploy | GitHub Actions workflow; stop committing built files | None, if done right |

Rough size: A is the largest (a few sessions). B and C are a session or two each. D is small.

After this, adding a region means: add places to `config/places.json` and a row to `config/regions.json`, run `openmeteo_fetch.py` (all places together, per HANDOVER 4.1) and any station scripts, then build.

## 5. Out of scope for this refactor

- The cycling-base score (its own design: `docs/cycling-score-spec.md`). Phase A's `summary.json` and phase B's map are what it will plug into.
- New regions and new data sources.
- Any change to thresholds or aggregation (HANDOVER 4.2 and 5.3).

## 6. Questions for the owner

1. OK to drop "works offline as a single file" (decision 2)?
2. OK to switch Pages to deploy via GitHub Actions (decision 5)? You'd need to change one repo setting.
3. Region URL style: `/spain-coast/` (my suggestion), or keep `.html` names such as `/spain-coast.html`?
4. Should the Spain dashboard stay one page with four sub-regions (as now), or become one page per costa? I'd keep one page per country or large area, with sub-region tabs as map shortcuts.

## Phase A: done (23 October 2026)

- `config/places.json` and `config/regions.json` replace `pipeline/places.json` and `data/processed/places-spain.json`. UK places now have `country: "GB"`, `baseline: true` and `setting: "Baseline"` (was "Home"; not shown anywhere).
- Data are split per country: `data/processed/climate/{ES,GB}.json` and `stations/ES.json`, with the same row schema; the split round-trips exactly. `openmeteo_fetch.py` and `stations_combine.py` read `config/places.json` and write per-country files.
- `site-src/` holds the page split into templates, CSS and JS. `build/build_site.py` builds `_site/`, with a columnar region file (Spain: 123 KB, against ~750 KB of row JSON) and `summary.json`. `src/` and `build_standalone.py` are removed.
- Checks:
  - `tests/data_check.py` passes (HANDOVER 4.4, with Bristol's hot days corrected from 0 to 1.2, a handover typo);
  - `tests/render_check.js _site` passes for both pages;
  - `tests/compare_pages.js` shows the new Spain page renders **identical markup** to the published one across 31 settings (only the map legend's random gradient id is normalised).
- Deviations from the plan:
  - the region page is already generated at `_site/spain-coast/` (the plan put this URL in phase C); the redirect from the old URL is still phase C;
  - the shim's `DEFAULTS` and the page's region constants are still hard-coded (phase C);
  - `site-src/` replaces `src/` rather than living beside it.
- The live site is unchanged: Pages still serves the frozen root files until phase D.

## Phase D: done (23 October 2026, brought forward ahead of B and C)

- `.github/workflows/deploy.yml` runs on every push to `main` (and manually): `npm ci`, Playwright Chromium, `build_site.py`, `data_check.py`, `render_check.js _site`, then publishes `_site/` with GitHub's official Pages actions. A failed step publishes nothing.
- The build writes `_site/spanish-coast-climate.html`, a redirect to `spain-coast/` that keeps any `#section`, so the old link works. (This was phase C in the plan; it was needed for D.)
- The frozen root `index.html` and `spanish-coast-climate.html` are removed. For before/after comparisons, take the old page from history: `git show 052c30e:spanish-coast-climate.html`.
- Checked by simulating the workflow in a fresh clone: clean `npm ci`, the build, both checks and the 31-setting comparison all pass; the redirect lands on `/spain-coast/#measured`. The workflow itself first runs on GitHub after the owner switches Pages to "GitHub Actions" and pushes.
- Saved dashboard settings don't carry over (the localStorage key changed); visitors start from the defaults once.
