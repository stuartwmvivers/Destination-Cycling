# Plan: adding Portugal (draft for the owner, 29 October 2026)

Status: **draft, not started.** The owner chose Portugal before France (29 October 2026), in line with the order in HANDOVER 9.4. Portugal is about a fifth of Spain's size, so it's a cheap first test of covering more than one country.

## 1. Inputs

| Input | Source | State on 29 Oct 2026 |
|---|---|---|
| Roads, paths, place names, restaurants | Geofabrik `portugal-latest.osm.pbf` (427 MB, data of 28 Oct 2026; includes Madeira and the Azores) | **Downloaded** into the cache, in `osm-portugal/`. It is kept out of `osm/` on purpose: every script reads all `*-latest.osm.pbf` there, so it would leak into the Spain rerun (DC-18). |
| Terrain | Copernicus DEM GLO-30 | **Mainland already cached** (Spain's tiles reach 10° W). Madeira needs 3 more tiles. |
| Land cover | ESA WorldCover | **Mainland already cached.** Madeira and Porto Santo need 2 more tiles. |
| Weather | Open-Meteo, same method (HANDOVER 4) | Roughly 100 points, under a day at the daily limit. Can't start until Spain's download finishes (they share the allowance). |
| Flights | Same rule as Spain (`config/airports.json`) | Wikipedia read on 29 Oct 2026 (below). Google Flights check for January and February still to do, as for Spain. |
| House prices | INE (Statistics Portugal), indicator 0012234: median €/m² of dwelling sales in the last 12 months, by municipality, quarterly. Free JSON API, no key. | **Downloaded** to the cache (`prices-portugal/`), quarter 2 2026: all 308 municipalities, as total, existing and new homes. |
| Station validation | IPMA or ECA&D | Later, as for the rest of Europe (HANDOVER 9.2). |

**Flights from Wikipedia (29 Oct 2026; "year-round" here means not marked seasonal, still to be checked against winter timetables):**
- Faro: Ryanair from Edinburgh; easyJet and Jet2 from Glasgow (Jet2 seasonal from Edinburgh).
- Lisbon: easyJet and Ryanair from Edinburgh; easyJet from Glasgow.
- Porto: Ryanair from Edinburgh; easyJet seasonal from Glasgow.
- Funchal (Madeira): Jet2 and Ryanair from Edinburgh; Jet2 from Glasgow.
- Azores: no direct flights from either.

## 2. Prices: easier than Spain

INE covers every municipality automatically, so there's no manual lookup on a portal. INE data is free to reuse with the source credited, unlike the notaries' data, so Portugal's prices *could* be public. The owner has chosen to keep them private for now (section 5), so they stay out of the repo, like Spain's.

Caveat: it's a municipal median of all sales (flats and houses together), like Spain's figure. Portuguese municipalities are large (308 for the country, against Spain's 8,000+), so one figure covers a wide area. INE also publishes parish figures, but only for larger places.

## 3. Code changes

1. **Inputs** (`common.py`, `fetch_inputs.py`): add the Portugal extract and Madeira's terrain and land-cover tiles.
2. **One road network across the border** (`build_network.py`): Geofabrik extracts overlap at the border, so ways that appear in both files must be counted once (shared nodes already join up, but duplicate ways would double road lengths). Then Spanish bases near Portugal can use Portuguese roads and climbs, and the other way round. The same de-duplication applies in `extract_features.py` and `extract_eating.py`.
3. **Grid** (`bases.py`): widen the mainland area to 9.6° W and add Madeira.
4. **Municipalities** (`municipalities.py`): in Portugal a municipality (concelho) is OSM `admin_level=7`; level 8 is a parish. Join INE prices by municipality code, or by name within district.
5. **Prices** (`price_join.py`, `price_shortlist.py`): the shortlist is only needed for Spain.
6. **Check lists** (`gate.py` and the `PLACES` lists): add known Portuguese places as tests, e.g. Monchique, Serra da Estrela (Covilhã), Sintra, Arrábida, Gerês and Funchal.
7. **Airports** (`config/airports.json`): add Faro, Lisbon, Porto and Funchal after the winter check.
8. **Output**: `data/processed/score/spain.json` becomes a file covering both countries; the site, mock-up and regions ("Go to" buttons, region filters) gain Portugal and Madeira.
9. **Credits**: INE (Statistics Portugal) on the page and in HANDOVER 6.

Spain's numbers should not change except near the border, where bases gain Portuguese roads. The data checks (HANDOVER 4.4) and a before/after comparison of Spain's ranking will show this.

## 4. Order

1. Now: downloads (done), flights check, this plan.
2. Tomorrow: Spain's weather finishes; the Spain rerun and price refresh (DC-18, DC-19) go first, unchanged, so the owner can recheck the ranking on its own.
3. Then the code changes above, with the network and climbs rebuilt for both countries (each step takes minutes, not hours).
4. Portugal's weather points (under a day of fetching), then the full score, prices and mock-up data.
5. The owner reviews Portugal's results against the known places.

## 5. Decisions (owner, 29 October 2026)

- **Madeira is included** (with Porto Santo): year-round direct flights from both airports, big climbs and mild winters. The Azores are left out for now: no direct flights.
- **Portugal's prices stay private**, like Spain's, until the owner decides otherwise, even though INE's data could be published (section 2).
