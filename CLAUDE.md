# CLAUDE.md — Destination-Cycling

Static site comparing year-round cycling climate (and, in future, terrain, roads and airport access) for candidate holiday-home locations. Hosted on GitHub Pages from this **public** repo.

**Start by reading `HANDOVER.md`** (full history, data method, decisions, roadmap), `docs/refactor-plan.md` (the multi-region refactor in progress) and `docs/cycling-score-spec.md` (the planned ranking).

## Rules

- **Public repo:** never commit personal information, API keys or tokens. Keys come from env vars (`METEOCAT_API_KEY`, `AEMET_API_KEY`, `CEDA_ACCESS_TOKEN`); see `.env.example`. Ask the owner for them.
- **Never commit raw daily Meteocat data** (`data/raw/` is git-ignored). Permission covers monthly summaries only. Credit every data source on the page (HANDOVER section 6).
- **Method stability:** thresholds and aggregation in HANDOVER 4.2 / 5.3 define every number. If you change them, say so explicitly and update the reference values in HANDOVER 4.4.
- **Verify before handing over:** `python3 build/build_site.py`, then `python3 tests/data_check.py` (HANDOVER 4.4 reference values) and `node tests/render_check.js _site` (no page errors, no horizontal overflow at 400 px). For refactors that shouldn't change the page, also `node tests/compare_pages.js`.
- Edit `site-src/`, `config/` and `data/processed/`, never `_site/` (build output, git-ignored). Pushing to `main` deploys via GitHub Actions (`.github/workflows/deploy.yml`) only if the build and checks pass.
- Propose structural changes (refactor, new data sources, map library) as a short plan before implementing.
- Ask the owner before pushing or publishing.
- British English. Be direct and state uncertainty plainly.

## Commands

```bash
npm ci && npx playwright install chromium
python3 build/build_site.py                       # -> _site/
python3 tests/data_check.py
node tests/render_check.js _site
node tests/serve.js _site 8000                    # preview at http://127.0.0.1:8000/ (file:// won't load data)
git show 052c30e:spanish-coast-climate.html > /tmp/old.html   # last single-file page, for before/after comparisons
node tests/compare_pages.js /tmp/old.html spain-climate-params _site spain-coast --skip-map   # map card differs since phase B
python3 pipeline/openmeteo_fetch.py --check <place_id>   # compare live API with committed rows, writes nothing
python3 pipeline/openmeteo_fetch.py <place_id>    # modelled data: fetch and WRITE (see HANDOVER 4.1 first)
METEOCAT_API_KEY=... python3 pipeline/meteocat_fetch.py && python3 pipeline/meteocat_aggregate.py
AEMET_API_KEY=...    python3 pipeline/aemet_fetch.py    && python3 pipeline/aemet_aggregate.py
python3 pipeline/stations_combine.py
```
