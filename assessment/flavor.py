"""
Sends a caught tree's actual cropped photo to Gemini (vision-capable) to
generate a fun, Pokedex-style catch card: a nerdy unique nickname, a
best-guess species/type, and a couple of interesting facts.

This is a *visual guess*, not real species identification -- detect.py's
model only knows "tree" (one class, no species classifier). Framing it
honestly as a guess is deliberate, not a limitation to hide.

Uses Gemini's structured-output mode (responseSchema) so the nickname comes
back as its own field, instead of trying to regex it out of free-form text.
"""
import base64
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-2.5-flash"

PROMPT = """You are a friendly, lightly nerdy guide for a citizen-science tree-spotting app.
Look at this photo of a tree that was just "caught" by a drone survey. Respond with:

- nickname: A short, fun catch-name for this specific tree with a light pun or bit of
  wordplay -- think Pokemon catch-name energy, not a biology lecture. A little nerdy is
  great, just don't pile on the jargon. Not necessarily a real species name.
- flavor: Your best guess at its likely species or general type, based on visible
  features (leaf/needle shape, bark, form) -- clearly labeled as a visual guess,
  not certain identification -- plus one or two genuinely interesting facts about
  that species or type. Under 70 words, nerdy but informative tone."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "nickname": {"type": "string"},
        "flavor": {"type": "string"},
    },
    "required": ["nickname", "flavor"],
}

def get_tree_flavor(image_path):
    """Returns {"nickname": str, "flavor": str}.
    Raises RuntimeError with a message safe to show a user."""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
            params={"key": API_KEY},
            json={
                "contents": [{"parts": [
                    {"text": PROMPT},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_data}},
                ]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": RESPONSE_SCHEMA,
                },
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except requests.HTTPError:
        raise RuntimeError(f"Flavor text service returned an error (status {resp.status_code}). Try again in a moment.") from None
    except requests.RequestException:
        raise RuntimeError("Couldn't reach the flavor text service. Check your connection and try again.") from None
    except (KeyError, IndexError, json.JSONDecodeError):
        raise RuntimeError("Got an unexpected response from the flavor text service.") from None

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python assessment/flavor.py <path-to-crop-image>")
    else:
        print(get_tree_flavor(path))
