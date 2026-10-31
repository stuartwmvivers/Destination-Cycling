# Plan: adding Portugal (29 October 2026)

Status: **built and published 31 October 2026** (results in section 6). Portugal's walking scores are still being checked. The owner chose Portugal before France (29 October 2026), in line with the order in HANDOVER 9.4. Portugal is about a fifth of Spain's size, so it's a cheap first test of covering more than one country.

## 1. Inputs

| Input | Source | State on 29 Oct 2026 |
|---|---|---|
| Roads, paths, place names, restaurants | Geofabrik `portugal-latest.osm.pbf` (427 MB, data of 28 Oct 2026; includes Madeira and the Azores) | **Downloaded** into the cache. It was kept in `osm-portugal/` until the Spain rerun finished; it is now in `osm/` with the other extracts, and Madeira's terrain and land-cover tiles are in `dem/` and `landcover/`. |
| Terrain | Copernicus DEM GLO-30 | **Mainland already cached** (Spain's tiles reach 10° W). Madeira needs 3 more tiles. |
| Land cover | ESA WorldCover | **Mainland already cached.** Madeira and Porto Santo need 2 more tiles. |
| Weather | Open-Meteo, same method (HANDOVER 4) | Roughly 100 points, under a day at the daily limit. Can't start until Spain's download finishes (they share the allowance). |
| Flights | Same rule as Spain (`config/airports.json`) | **Checked 29 Oct 2026** (below). All four airports qualify as year-round. |
| House prices | INE (Statistics Portugal), indicator 0012234: median €/m² of dwelling sales in the last 12 months, by municipality, quarterly. Free JSON API, no key. | **Downloaded** to the cache (`prices-portugal/`), quarter 2 2026: all 308 municipalities, as total, existing and new homes. |
| Station validation | IPMA or ECA&D | Later, as for the rest of Europe (HANDOVER 9.2). |

**Flights (checked 29 Oct 2026, the same way as Spain's):** Wikipedia's Edinburgh and Glasgow airline lists, then Google Flights direct-only one-way searches on and around Wed 13 Jan and Wed 10 Feb 2027. Frequencies are estimates from those searches, not timetables. Re-check each autumn.

| Airport | From Edinburgh, mid-January | From Glasgow | Status |
|---|---|---|---|
| Faro (FAO) | Ryanair, about 2 a week (Mon, Sat); 3 in February | None found in mid-January (easyJet and Jet2 back by February) | Year-round (via Edinburgh), only just meeting "about twice a week" |
| Lisbon (LIS) | Ryanair, about 5 a week | None found in mid-January (easyJet by February) | Year-round |
| Porto (OPO) | Ryanair, about 3 a week (Sun, Mon, Fri) | None in January; from February | Year-round (via Edinburgh) |
| Funchal, Madeira (FNC) | Jet2, 2 a week (Mon, Thu) | Jet2, weekly (Mon) | Year-round |

The Azores have no direct flights from either airport.

**Not yet in `config/airports.json`:** the Spain rerun (DC-18) reads that file on a Spain-only road network, which would snap Portuguese airports onto the nearest Spanish road and give wrong drive times. Add them with the code changes in section 3 (coordinates: FAO 37.014, -7.966; LIS 38.774, -9.134; OPO 41.248, -8.681; FNC 32.698, -16.774).

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
7. **Airports** (`config/airports.json`): add Faro, Lisbon, Porto and Funchal (section 1), once the network covers Portugal.
8. **Output**: `data/processed/score/spain.json` becomes a file covering both countries; the site, mock-up and regions ("Go to" buttons, region filters) gain Portugal and Madeira.
9. **Credits**: INE (Statistics Portugal) on the page and in HANDOVER 6.

Spain's numbers should not change except near the border, where bases gain Portuguese roads. The data checks (HANDOVER 4.4) and a before/after comparison of Spain's ranking will show this.

## 4. Order

1. Now: downloads, flights check and this plan (all done 29 Oct 2026).
2. Tomorrow: Spain's weather finishes; the Spain rerun and price refresh (DC-18, DC-19) go first, unchanged, so the owner can recheck the ranking on its own.
3. Then the code changes above, with the network and climbs rebuilt for both countries (each step takes minutes, not hours).
4. Portugal's weather points (under a day of fetching), then the full score, prices and mock-up data.
5. The owner reviews Portugal's results against the known places.

## 5. Decisions (owner, 29 October 2026)

- **Madeira is included** (with Porto Santo): year-round direct flights from both airports, big climbs and mild winters. The Azores are left out for now: no direct flights.
- **Portugal's prices stay private**, like Spain's, until the owner decides otherwise, even though INE's data could be published (section 2).

## 6. What was built and found (31 October 2026)

**Totals:** 19,956 bases on the 5 km grid, 9,216 past the gate; 4,126 climbs (68 in Madeira); 683 weather points; 101 areas in the mock-up (82 in Spain, 19 in Portugal, 5 of them in Madeira).

**Known places** (rank among the 9,216 gate-passing bases, default weights):

| Place | Expected | Gate | Rank | Weakest parts |
|---|---|---|---|---|
| Monchique | pass | pass | 903 | Walking |
| Sintra | ? | pass | 1,792 | Gravel, walking |
| Funchal | pass | pass | 2,740 | Gravel, flat roads |
| Vila do Gerês | pass | pass | 3,780 | Weather (wet), flat roads |
| Covilhã (Serra da Estrela) | pass | pass | 5,108 | Walking, quiet roads |
| Azeitão (Arrábida) | ? | fail | - | Too few climbs nearby |
| Aveiro, Beja | fail | fail | - | As expected |

The best Portuguese areas in the default list are Montaria (47th), Silves (49th) and Madalena do Mar (51st). Mainland Portugal falls short of Spain on weather and, more sharply, walking: across the listed areas it averages 0.61 against 0.80 for weather and 0.13 against 0.58 for walking.

**Portugal's walking score needs a check.** The median Portuguese gate-passing base has 267 km of mapped walking paths and 19 named peaks within reach, against 615 km and 109 in Spain east of 6° W. Some of that will be real, since Portugal has fewer high mountains, but some may be thinner OpenStreetMap mapping, and this hasn't been tested. Walking carries 10% of the score, so it could be holding Portuguese areas back by several points. Monchique's 0.09 looks low for a place on the Via Algarviana.

**Madeira's weather needed smaller cells.** With 25 km cells, one model point on the island's spine served both coasts, giving Funchal 152 wet days and 180 windy days a year. The model's cell on the south coast gives 114 and 104. For comparison, real Funchal has about 80 wet days a year on a third-party figure, not IPMA's own, so the coastal cell overcounts by about 40%, in line with the 30–70% measured in Spain (HANDOVER 5.4), and the spine point by about double. Madeira and Porto Santo now use 10 km cells (`common.weather_cell`), and include every base with a near climb, so Porto Santo no longer borrows from Madeira. The rideable-day rule and every other area's points are unchanged. Funchal's weather component went from 0.11 to 0.47.

Madeira's figures are still pessimistic and less certain than the mainland's. The model can't resolve the island's steep terrain, and there's no station check there yet. The same risk applies in principle to the smaller Canary Islands, whose 25 km cells were not changed.

**Spain, before and after** (published file against the new one, 10,734 bases in both):

- Spanish grid points and climbs: 16,609 of 16,609 bases are at the same grid point, and 3,107 of 3,113 climbs are identical (the others are border climbs).
- Rank correlation 0.99; all of the old top 50 are still in the top 200, and 46 in the top 50. The top ten are the same bases in a slightly different order.
- East of 6° W only 1 of 8,306 bases moved by more than one point. The small shifts everywhere come from the method, not from changed data: components are scaled between the 5th and 95th percentile of gate-passing bases, and those now include Portugal.
- West of 6° W, 1,026 of 2,428 bases moved by more than a point, up to +18: 1,399 bases now have Porto as their nearest year-round airport, instead of Santander (990) or Madrid (409), and 2 have Lisbon. 7 border bases passed the gate because of climbs in Portugal.
- 28 bases near the border are at slightly different positions, so they aren't matched in the count above. None is east of 6° W.
- Every Spanish base with a price kept the same figure.
- This qualifies section 3's "should not change except near the border": every Spanish score can shift slightly, usually by less than a point, whenever a new area is added.

**Prices:** 24 more Spanish lookups were needed (`docs/price-data-plan.md`), 12 of them in Galicia, where Porto's airport lifted the score. Portugal's 308 municipalities come from INE; 304 matched OSM.

**A fetch stopped overnight** on 31 October after 23 of the 99 new points, with no error logged. Rerunning it resumed from where it stopped.
