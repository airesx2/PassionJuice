"""
Placeholder zone data for the map feature, standing in for what real
GPS-clustered catches will look like once detect.py logs coordinates.

Each zone is a rough area with a center point and a catch count -- later,
this will be built by clustering real (lat, lon) values from log.csv instead
of being hardcoded here. The map code that consumes this doesn't need to
change when that swap happens, only where this list comes from.
"""

SAMPLE_ZONES = [
    {"id": "zone-a", "name": "North Ridge",  "lat": 45.5231, "lon": -122.6765, "catch_count": 14},
    {"id": "zone-b", "name": "Creek Bottom",  "lat": 45.5198, "lon": -122.6820, "catch_count": 4},
    {"id": "zone-c", "name": "South Slope",   "lat": 45.5165, "lon": -122.6790, "catch_count": 21},
    {"id": "zone-d", "name": "West Clearing", "lat": 45.5210, "lon": -122.6910, "catch_count": 2},
]

def get_zones():
    return SAMPLE_ZONES

def get_zone(zone_id):
    for z in SAMPLE_ZONES:
        if z["id"] == zone_id:
            return z
    return None
