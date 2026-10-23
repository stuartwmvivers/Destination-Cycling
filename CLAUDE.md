# CLAUDE.md — Destination-Cycling

Static site comparing year-round cycling climate (and, in future, terrain, roads and airport access) for candidate holiday-home locations. Hosted on GitHub Pages from this **public** repo.

**Start by reading `HANDOVER.md`** (full history, data method, decisions, roadmap) and `docs/cycling-score-spec.md` (the planned ranking).

## Rules

- **Public repo:** never commit personal information, API keys or tokens. Keys come from env vars (`METEOCAT_API_KEY`, `AEMET_API_KEY`, `CEDA_ACCESS_TOKEN`); see `.env.example`. Ask the owner for them.
- **Never commit raw daily Meteocat data** (`data/raw/` is git-ignored). Permission covers monthly summaries only. Credit every data source on the page (HANDOVER section 6).
- **Method stability:** thresholds and aggregation in HANDOVER 4.2 / 5.3 define every number. If you change them, say so explicitly and update the reference values in HANDOVER 4.4.
- **Verify before handing over:** `python3 build/build_standalone.py` then `node tests/render_check.js spanish-coast-climate.html` (no page errors, no horizontal overflow at 400 px).
- Propose structural changes (refactor, new data sources, map library) as a short plan before implementing.
- Ask the owner before pushing or publishing.
- British English. Be direct and state uncertainty plainly.

## Commands

```bash
npm ci
python3 build/build_standalone.py                 # -> spanish-coast-climate.html
node tests/render_check.js spanish-coast-climate.html
python3 pipeline/openmeteo_fetch.py <place_id>    # modelled data (verify vs committed rows first)
METEOCAT_API_KEY=... python3 pipeline/meteocat_fetch.py && python3 pipeline/meteocat_aggregate.py
AEMET_API_KEY=...    python3 pipeline/aemet_fetch.py    && python3 pipeline/aemet_aggregate.py
python3 pipeline/stations_combine.py
```
