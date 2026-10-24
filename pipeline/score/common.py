"""Shared settings for the cycling-base score pipeline (docs/score-prototype-plan.md).

Large inputs and intermediates live in the cache folder named by DC_CACHE (outside OneDrive and git);
only small results are written into the repo.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.environ.get('DC_CACHE')
if not CACHE or not os.path.isdir(CACHE):
    sys.exit('Set DC_CACHE to the cache folder (e.g. C:\\ai-projects\\DestinationCyclingCache) and create it first')
OSM = os.path.join(CACHE, 'osm')
DEM = os.path.join(CACHE, 'dem')
WORK = os.path.join(CACHE, 'work')
for d in (OSM, DEM, WORK): os.makedirs(d, exist_ok=True)

# OpenStreetMap extracts (Geofabrik): Spain excludes the Canaries, which are listed under Africa.
OSM_EXTRACTS = {
    'spain': 'https://download.geofabrik.de/europe/spain-latest.osm.pbf',
    'canary-islands': 'https://download.geofabrik.de/africa/canary-islands-latest.osm.pbf',
}
# Copernicus DEM GLO-30 one-degree tiles covering mainland Spain + Balearics, and the Canaries.
# Tiles named by their south-west corner; all-sea tiles don't exist (404) and are skipped.
DEM_URL = 'https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif'
DEM_AREAS = [(range(35, 44), range(-10, 5)),     # lat 35-43 N, lon 10 W - 4 E
             (range(27, 30), range(-19, -13))]    # Canaries: lat 27-29 N, lon 19-14 W

def dem_name(lat, lon):
    return f"Copernicus_DSM_COG_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00_DEM"
