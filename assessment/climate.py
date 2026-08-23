"""
Step 1 of the climate-smart planting feature: given a ZIP code for a survey
site, fetch the raw environmental facts we'll eventually feed to an LLM.

Three free, no-API-key services, chained together:
  ZIP code -> lat/lon        (zippopotam.us)
  ZIP code -> hardiness zone (phzmapi.org)
  lat/lon  -> climate normals (open-meteo.com)

"""
import requests #Http calls from Python

def get_lat_lon(zip_code):
    resp = requests.get(f"https://api.zippopotam.us/us/{zip_code}", timeout=10)
    resp.raise_for_status()
    place = resp.json()["places"][0]
    return float(place["latitude"]), float(place["longitude"])

def get_hardiness_zone(zip_code):
    resp = requests.get(f"https://phzmapi.org/{zip_code}.json", timeout=10)
    resp.raise_for_status()
    return resp.json()["zone"]

def get_climate_normals(lat, lon):
    """10-year daily averages, boiled down to one annual precipitation
    total (mm) and one mean temperature (C)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2014-01-01",
        "end_date": "2023-12-31",
        "daily": "temperature_2m_mean,precipitation_sum",
        "models": "MRI_AGCM3_2_S",
    }
    resp = requests.get("https://climate-api.open-meteo.com/v1/climate", params=params, timeout=20)
    resp.raise_for_status()
    daily = resp.json()["daily"]

    temps = [t for t in daily["temperature_2m_mean"] if t is not None]
    rain = [r for r in daily["precipitation_sum"] if r is not None]
    num_years = len(temps) / 365

    return {
        "avg_temp_c": round(sum(temps) / len(temps), 1),
        "avg_annual_precip_mm": round(sum(rain) / num_years, 0),
    }

def get_site_climate_profile(zip_code):
    """Combine all three lookups into one dict, or raise with msg
    that's safe to show the user (bad zip, API down, etc.)."""
    try:
        zone = get_hardiness_zone(zip_code)
        lat, lon = get_lat_lon(zip_code)
        climate = get_climate_normals(lat, lon)
    except (requests.RequestException, KeyError, IndexError, ValueError) as e:
        raise RuntimeError(f"Couldn't look up climate data for ZIP {zip_code}: {e}")

    return {
        "zip": zip_code,
        "lat": lat,
        "lon": lon,
        "hardiness_zone": zone,
        **climate,
    }

def get_zip_from_latlon(lat, lon):
    resp = requests.get("https://nominatim.openstreetmap.org/reverse",params={"format":"json","lat":lat,"lon":lon},
                        headers={"User-Agent": "tree-dex-capstone"}, timeout=10)
    resp.raise_for_status()
    address = resp.json().get("address", {}) #nest all location details
    zip_code = address.get("postcode") #specifically zip 
    if not zip_code: 
        raise RuntimeError(f"Couldn't find ZIP code for lat={lat}, lon={lon}")
    return zip_code

if __name__ == "__main__":
    import sys
    zip_code = sys.argv[1] if len(sys.argv) > 1 else "97201"
    profile = get_site_climate_profile(zip_code)
    for k, v in profile.items():
        print(f"{k}: {v}")
