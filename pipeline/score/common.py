"""Shared settings for the cycling-base score pipeline (docs/score-prototype-plan.md).

Large inputs and intermediates live in the cache folder named by DC_CACHE (outside OneDrive and git);
only small results are written into the repo.
"""
import math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.environ.get('DC_CACHE')
if not CACHE or not os.path.isdir(CACHE):
    sys.exit('Set DC_CACHE to the cache folder (e.g. C:\\ai-projects\\DestinationCyclingCache) and create it first')
OSM = os.path.join(CACHE, 'osm')
DEM = os.path.join(CACHE, 'dem')
LANDCOVER = os.path.join(CACHE, 'landcover')
WORK = os.path.join(CACHE, 'work')
for d in (OSM, DEM, LANDCOVER, WORK): os.makedirs(d, exist_ok=True)

SCORE_JSON = os.path.join(ROOT, 'data', 'processed', 'score', 'bases.json')

# Weather cells: 25 km squares, but 10 km on Madeira and Porto Santo. A wider square there spans both coasts and the
# mountains between, and one point on the spine is far wetter and windier than the coast (Funchal 152 wet days a year
# against 114 at the coast). Open-Meteo's cells are about 8 x 10 km, so this is close to one point per model cell.
MADEIRA_CELL_KM = 10.0

def in_madeira(lat):
    return 32 < lat < 34

def weather_cell(lat, lon, km):
    if in_madeira(lat): km = MADEIRA_CELL_KM
    return math.floor(lat * 111.2 / km), math.floor(lon * 111.2 * math.cos(math.radians(lat)) / km)

# OpenStreetMap extracts (Geofabrik): Spain excludes the Canaries, which are listed under Africa. Portugal includes
# Madeira and the Azores. Extracts overlap at borders (12,280 highway ways are in both Spain and Portugal, none cut
# short), so every script that reads them counts each OSM object once, keeping the first copy it meets.
OSM_EXTRACTS = {
    'spain': 'https://download.geofabrik.de/europe/spain-latest.osm.pbf',
    'canary-islands': 'https://download.geofabrik.de/africa/canary-islands-latest.osm.pbf',
    'portugal': 'https://download.geofabrik.de/europe/portugal-latest.osm.pbf',
}
# Copernicus DEM GLO-30 one-degree tiles covering mainland Spain and Portugal + Balearics, the Canaries, and Madeira.
# Tiles named by their south-west corner; all-sea tiles don't exist (404) and are skipped.
DEM_URL = 'https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif'
DEM_AREAS = [(range(35, 44), range(-10, 5)),     # lat 35-43 N, lon 10 W - 4 E
             (range(27, 30), range(-19, -13)),    # Canaries: lat 27-29 N, lon 19-14 W
             (range(32, 34), range(-18, -16))]    # Madeira and Porto Santo: lat 32-33 N, lon 18-17 W

def dem_name(lat, lon):
    return f"Copernicus_DSM_COG_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00_DEM"

# ESA WorldCover 2021 (10 m land cover, CC BY 4.0): 3x3-degree tiles named by their south-west corner.
# Used for countryside quality (gravel) and to leave out urban footways (walking). Replaces CORINE in the
# plan: CORINE needs an EU login to download; WorldCover doesn't, and is newer and finer.
LANDCOVER_URL = 'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif'
LANDCOVER_TILES = [f"N{la:02d}{'E' if lo >= 0 else 'W'}{abs(lo):03d}" for la in (36, 39, 42) for lo in range(-12, 4, 3)] + \
                  [f"N27W{lo:03d}" for lo in (21, 18, 15)] + ['N30W018', 'N33W018']
