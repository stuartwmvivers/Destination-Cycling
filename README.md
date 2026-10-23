# Destination Cycling

A free, static website comparing places in Europe as **year-round road-cycling bases**. It starts with climate: how many good riding days each place gets, month by month, against two UK baselines (Dunning in Perthshire and Bristol), and how far to trust those figures.

**Site:** https://stuartwmvivers.github.io/Destination-Cycling/

| Page | What it shows |
|---|---|
| [Landing page](https://stuartwmvivers.github.io/Destination-Cycling/) | What the site is, regions covered, rideable days a year for every place |
| [Spanish coast](https://stuartwmvivers.github.io/Destination-Cycling/spanish-coast-climate.html) | 20 places on the Costa Brava, Costa del Sol, Costa Blanca and Mallorca, 2017–2025: map, seasonal charts, every month of every year, and a model-vs-weather-station comparison for 17 towns |

## How the figures are made

- **Modelled weather** for every place comes from the [Open-Meteo](https://open-meteo.com/) historical archive (ECMWF analysis, about 9 km grid), daily for 2017–2025, aggregated to monthly measures.
- A **rideable day** is dry (under 1 mm), with gusts under 50 km/h and a high of at least 11 °C. A **warm riding day** needs a high of 14–30 °C under the same conditions. The page also shows highs, lows, rainfall, wet days, hot days, frost nights and north-wind (Tramuntana) days.
- **Station checks:** 17 towns are paired with a nearby real weather station (Meteocat in Catalonia, AEMET elsewhere). Everywhere checked, the model counts too many wet days, so real rideable days are as many as modelled or more. Temperature bias varies by region, so no correction is applied; model and station are shown side by side.

Full method, thresholds and decisions: [HANDOVER.md](HANDOVER.md).

## Plans

- More regions: the rest of Spain (including the Canaries), then Portugal, France and the UK, later Italy, Croatia and Slovenia.
- A combined **cycling-base score** weighting climbing most, then weather at the climbs' altitude, quiet roads and airport access. Design: [docs/cycling-score-spec.md](docs/cycling-score-spec.md).

## Building

Needs Python 3 and Node.js.

```bash
npm ci
npx playwright install chromium     # once, for the tests
python3 build/build_site.py         # -> _site/ (landing page, one dashboard per region, data files)
python3 tests/data_check.py         # reference values and data integrity
node tests/render_check.js _site    # every page, desktop and phone
node tests/serve.js _site 8000      # preview at http://127.0.0.1:8000/
```

What to build comes from `config/places.json` and `config/regions.json`; monthly data from `data/processed/`; page templates, styles and scripts from `site-src/`. Pages fetch their data, so preview them through the local server rather than opening the files directly.

A refactor towards multiple regions is in progress ([docs/refactor-plan.md](docs/refactor-plan.md)). Until it switches deployment to GitHub Actions, the live site is served from the frozen `index.html` and `spanish-coast-climate.html` at the repo root.

Data pipeline scripts are in `pipeline/`; see HANDOVER.md for how to run them (station data needs API keys, which are never committed).

## Credits and licences

- Weather model data: [Open-Meteo](https://open-meteo.com/), CC BY 4.0 (non-commercial free tier).
- Costa Brava station readings: © Servei Meteorològic de Catalunya (Meteocat), monthly summaries used with permission. Raw daily data is not redistributed.
- Costa del Sol, Costa Blanca and Mallorca station readings: © AEMET, Agencia Estatal de Meteorología.
- Map outlines: geo-maps (© OpenStreetMap contributors, ODbL), Natural Earth, es-atlas.
- Charts: [d3](https://d3js.org/) (ISC licence).
