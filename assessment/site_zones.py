"""
Zone data for the map feature.

get_zones() tries two real sources before falling back to sample data:
  1. Live GPS already sitting directly in dex/log.csv -- once detect.py is
     wired to the FC over MSP, it writes real latitude/longitude on every
     row itself, no post-processing needed at all.
  2. The older post-flight approach: match catches to a separately
     exported Blackbox CSV by timestamp, via geotag.py. This is what ran
     before live MSP wiring existed, and stays as a fallback for it.
If neither has anything usable, falls back to hardcoded SAMPLE_ZONES,
and says so via is_real=False.

Once detect.py starts writing live coordinates, source 1 takes over
automatically -- no code changes needed here at all, only real data
showing up where there wasn't any before.
"""
import os

from assessment.geotag import load_gps_track, load_catches_raw, enrich_catches

LOG_FILE = os.path.join("dex", "log.csv")
GPS_LOG_PATH = os.path.join("flight-logs", "btfl_008.csv")  # only used by the source-2 fallback

SAMPLE_ZONES = [
    {"id": "zone-a", "name": "North Ridge",  "lat": 45.5231, "lon": -122.6765, "catch_count": 14},
    {"id": "zone-b", "name": "Creek Bottom",  "lat": 45.5198, "lon": -122.6820, "catch_count": 4},
    {"id": "zone-c", "name": "South Slope",   "lat": 45.5165, "lon": -122.6790, "catch_count": 21},
    {"id": "zone-d", "name": "West Clearing", "lat": 45.5210, "lon": -122.6910, "catch_count": 2},
]

def _zones_from_geotagged(geotagged_catches):
    """Shared helper: turn a list of catches that already have
    latitude/longitude (however they got there) into one zone per catch."""
    zones = []
    for i, c in enumerate(geotagged_catches):
        lat, lon = c.get("latitude"), c.get("longitude")
        if lat is None or lon is None or lat == "" or lon == "":
            continue
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        name = (c.get("nickname") or "").strip() or "Tree"
        zones.append({"id": f"catch-{i}", "name": name, "lat": lat, "lon": lon, "catch_count": 1})
    return zones

def build_real_zones():
    """One zone per catch with real coordinates, live data preferred over
    post-flight matching. Returns [] if neither source has anything."""
    if not os.path.exists(LOG_FILE):
        return []
    catches = load_catches_raw(LOG_FILE)

    # Source 1: live GPS already in log.csv (detect.py wired to the FC over MSP)
    live_zones = _zones_from_geotagged(catches)
    if live_zones:
        return live_zones

    # Source 2: fall back to matching against a separately exported Blackbox CSV
    if not os.path.exists(GPS_LOG_PATH):
        return []
    try:
        track = load_gps_track(GPS_LOG_PATH)
    except (RuntimeError, OSError):
        return []
    return _zones_from_geotagged(enrich_catches(catches, track))

def get_zones():
    """Returns (zones, is_real) -- is_real tells the caller whether these
    are genuine GPS-matched catches or the sample placeholder data."""
    real_zones = build_real_zones()
    if real_zones:
        return real_zones, True
    return SAMPLE_ZONES, False

def get_zone(zone_id):
    zones, _ = get_zones()
    for z in zones:
        if z["id"] == zone_id:
            return z
    return None
