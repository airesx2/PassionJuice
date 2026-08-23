"""
Step 2 of the climate-smart planting feature: turn a site's climate profile
+ Tree Dex catch count into an actual planting recommendation via Gemini.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-2.5-flash"  # gemini-flash-latest was intermittently overloaded (503s)

def build_prompt(climate_profile, catch_count):
    return f"""You are an environmental planning assistant helping a citizen-science
tree-mapping project recommend plants for a specific site, with two goals:

1. Climate resilience: species that tolerate the shifting conditions this site
   is likely to see (heat, drought, storms) and that help mitigate climate
   change itself (strong carbon sequestration, canopy cover, soil health).
2. Ecological support: prioritize native species that support local pollinators,
   birds, and wildlife -- and call out if a recommended species is known to
   support any threatened or endangered species in its native range (e.g. a
   host plant for an endangered pollinator, or habitat for an at-risk bird).
   Avoid invasive or non-native species that could crowd out local ecosystems.

Site facts:
- USDA Plant Hardiness Zone: {climate_profile['hardiness_zone']}
- Average annual temperature: {climate_profile['avg_temp_c']} C
- Average annual rainfall: {climate_profile['avg_annual_precip_mm']} mm
- Trees detected during one aerial drone survey of this site: {catch_count}
  (this reflects one flight's coverage, not total site canopy density)

Recommend 3-5 plant species well-suited to this hardiness zone and climate.
For each, briefly cover: why it's climate-resilient, its role in carbon
capture or ecosystem health, and any wildlife or endangered-species benefit.
Keep the whole response under 220 words, written for a general audience,
not a botanist."""

def get_planting_recommendation(climate_profile, catch_count):
    """Raises RuntimeError with a message safe to show a user -- never
    includes the request URL, since that URL contains the API key."""
    prompt = build_prompt(climate_profile, catch_count)
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
            params={"key": API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except requests.HTTPError:
        raise RuntimeError(f"Recommendation service returned an error (status {resp.status_code}). Try again in a moment.") from None
    except requests.RequestException:
        raise RuntimeError("Couldn't reach the recommendation service. Check your connection and try again.") from None
    except (KeyError, IndexError):
        raise RuntimeError("Got an unexpected response from the recommendation service.") from None

if __name__ == "__main__":
    import sys
    from climate import get_site_climate_profile
    zip_code = sys.argv[1] if len(sys.argv) > 1 else "97201"
    profile = get_site_climate_profile(zip_code)
    print(get_planting_recommendation(profile, catch_count=12))
