"""
Match each tree catch in dex/log.csv to the GPS coordinates recorded
closest in time, using a real Blackbox CSV export (Configurator ->
Blackbox Viewer -> CSV button).

Real format, confirmed against an actual export (btfl_008.csv):
  - The file starts with ~150 lines of "key","value" metadata pairs,
    including "Log start datetime" -- a real UTC timestamp that anchors
    the rest of the log's relative time values to the real world.
  - After that comes the actual data table. Its header row isn't at a
    fixed line number (varies per file), so we find it by searching for
    the row containing "GPS_numSat".
  - Relevant columns: time (microseconds since log start, NOT wall-clock),
    GPS_numSat, GPS_coord[0] (latitude, degrees x 1e7), GPS_coord[1]
    (longitude, degrees x 1e7).
  - Rows recorded before GPS got a fix show "NaN" in these fields.

IMPORTANT CAVEAT: "Log start datetime" is UTC. detect.py's catch
timestamps come from the Pi's local system clock via datetime.now(),
which is only correct here if the Pi's clock is *also* set to UTC.
If matched timestamps end up looking wildly wrong (off by several
hours), check the Pi's timezone with `timedatectl` -- that's the
likely cause, not a bug in this script.
"""
import csv
from datetime import datetime, timedelta

CATCH_TIME_FORMAT = "%Y%m%d_%H%M%S"
MAX_MATCH_GAP_SECONDS = 60  # a catch and its "closest" GPS point still shouldn't
                            # be from different flights -- refuse the match instead
                            # of silently pairing unrelated data

def load_gps_track(csv_path):
    """Parse a Blackbox CSV export into a list of (datetime, lat, lon)
    tuples, anchored to real (UTC) wall-clock time."""
    with open(csv_path, newline="") as f:
        lines = f.readlines()

    log_start = None
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith('"Log start datetime"'):
            value = next(csv.reader([line]))[1]
            log_start = datetime.fromisoformat(value).replace(tzinfo=None)
        if '"GPS_numSat"' in line:
            header_idx = i
            break

    if log_start is None or header_idx is None:
        raise RuntimeError("Couldn't find 'Log start datetime' or the GPS header row in this CSV export.")

    header = next(csv.reader([lines[header_idx]]))
    time_i = header.index("time")
    numsat_i = header.index("GPS_numSat")
    lat_i = header.index("GPS_coord[0]")
    lon_i = header.index("GPS_coord[1]")

    track = []
    for row in csv.reader(lines[header_idx + 1:]):
        if len(row) <= lon_i:
            continue
        if row[numsat_i].strip() in ("", "NaN", "0"):
            continue  # no GPS fix yet at this point in the flight
        try:
            rel_micros = int(row[time_i])
            lat = int(row[lat_i]) / 1e7
            lon = int(row[lon_i]) / 1e7
        except ValueError:
            continue
        track.append((log_start + timedelta(microseconds=rel_micros), lat, lon))

    return track

def load_catches_raw(log_file):
    """Like app.py's load_catches, but keeps the raw timestamp string
    instead of formatting it for display -- we need it parseable here."""
    with open(log_file, newline="") as f:
        return list(csv.DictReader(f))

def find_closest_gps(catch_time, gps_track):
    """gps_track: list of (datetime, lat, lon) tuples.
    Returns (lat, lon) of whichever point's timestamp is nearest to catch_time,
    or None if even the closest point is more than MAX_MATCH_GAP_SECONDS away --
    that means the catch and the GPS log are from different flights entirely,
    and pairing them would just be a coincidence, not a real match."""
    closest = min(gps_track, key=lambda point: abs((point[0] - catch_time).total_seconds()))
    gap = abs((closest[0] - catch_time).total_seconds())
    if gap > MAX_MATCH_GAP_SECONDS:
        return None
    return closest[1], closest[2]

def enrich_catches(catches, gps_track):
    """Adds 'latitude' and 'longitude' to each catch dict, matched by
    closest timestamp -- only when that closest point is actually close in
    time (see find_closest_gps). Catches with an unparseable timestamp, no
    GPS track at all, or no sufficiently-close GPS point get None for both."""
    enriched = []
    for catch in catches:
        lat = lon = None
        if gps_track:
            try:
                catch_time = datetime.strptime(catch["timestamp"], CATCH_TIME_FORMAT)
                match = find_closest_gps(catch_time, gps_track)
                if match:
                    lat, lon = match
            except (ValueError, KeyError):
                pass
        enriched.append({**catch, "latitude": lat, "longitude": lon})
    return enriched

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python assessment/geotag.py <path-to-blackbox-csv-export> [path-to-log.csv]")
    else:
        gps_csv = sys.argv[1]
        log_file = sys.argv[2] if len(sys.argv) > 2 else "dex/log.csv"
        track = load_gps_track(gps_csv)
        print(f"Loaded {len(track)} real GPS points from {gps_csv}")
        catches = load_catches_raw(log_file)
        enriched = enrich_catches(catches, track)
        for c in enriched[:5]:
            print(c["timestamp"], "->", c["latitude"], c["longitude"])
