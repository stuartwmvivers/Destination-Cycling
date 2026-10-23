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
npx playwright install chromium                    # once, for the smoke test
python3 build/build_standalone.py                  # -> spanish-coast-climate.html and index.html
node tests/render_check.js spanish-coast-climate.html
node tests/render_check.js index.html
```

The built pages are committed because GitHub Pages serves them straight from `main`. Edit `src/`, not the built files. Data pipeline scripts are in `pipeline/`; see HANDOVER.md for how to run them (station data needs API keys, which are never committed).

## Credits and licences

- Weather model data: [Open-Meteo](https://open-meteo.com/), CC BY 4.0 (non-commercial free tier).
- Costa Brava station readings: © Servei Meteorològic de Catalunya (Meteocat), monthly summaries used with permission. Raw daily data is not redistributed.
- Costa del Sol, Costa Blanca and Mallorca station readings: © AEMET, Agencia Estatal de Meteorología.
- Map outlines: geo-maps (© OpenStreetMap contributors, ODbL), Natural Earth, es-atlas.
- Charts: [d3](https://d3js.org/) (ISC licence).
