# Tree Dex — Aerial Land Assessment for Climate-Smart Planting

A self-built 5" FPV quadcopter surveys land from above and detects trees/vegetation
in real time. Every detection is "caught" into a Pokédex-style web collection (the
fun front-end) — complete with an AI-generated nickname and flavor text for each
tree — while the same catch data quietly feeds a real environmental-impact feature
underneath: climate-aware planting recommendations powered by real climate data
and Gemini.

## Hardware

- Frame: QAV250
- Flight controller: SpeedyBee F405
- Motors: T-Motor V2306
- GPS: M8N
- Companion computer: Raspberry Pi Zero 2W + Camera Module V2

## Architecture

Two machines, two jobs:

- **Pi (weak, in the air)** — [detection/detect.py](detection/detect.py) captures a
  frame, runs a custom-trained YOLOv8 model (exported to ONNX) via `onnxruntime`,
  applies Non-Max Suppression to collapse duplicate/overlapping detections, and
  logs each surviving detection to `dex/log.csv` with a cropped image in
  `dex/crops/`. No PyTorch, no heavy web stack — this box just needs to detect and log.
- **Laptop (strong, on the ground)** — [app.py](app.py) is a Flask app that reads
  `dex/log.csv`, renders the Tree Dex card grid, and hosts the impact-layer
  features, which need internet access for climate-data APIs and Gemini calls.

```
detection/   Pi-side: model (best.onnx) + detection script
dex/         Shared data: catch log (log.csv) + cropped images (crops/)
assessment/  Impact-layer modules (climate lookup, LLM reasoning, sample zone data)
app.py       Laptop-side: Flask front-end + API routes
```

**assessment/ modules:**
- `climate.py` — ZIP code → USDA hardiness zone + rainfall/temperature normals
  (zippopotam.us, phzmapi.org, open-meteo.com — all free, no API key). Also
  reverse-geocodes lat/lon → ZIP (nominatim.openstreetmap.org) for the map feature.
- `recommend.py` — climate profile + catch count → a Gemini-generated planting
  recommendation, weighted toward climate resilience, carbon capture, and
  native/endangered species support.
- `flavor.py` — sends a caught tree's actual photo to Gemini (vision) and gets
  back a structured `{nickname, flavor}` — a fun catch-name and a visually-guessed
  species with a couple of facts. Framed honestly as a guess, since the detection
  model only classifies "tree" (one class, no species classifier).
- `site_zones.py` — hardcoded placeholder zones for the Map tab, standing in for
  what real GPS-clustered catches will look like once detections carry real
  coordinates (see Roadmap below).
- `zones.py` — an early, now-unused sketch (splitting a single image into a pixel
  grid). Superseded by the zone/map approach above.
- `test_gemini.py` — standalone connectivity smoke test for the Gemini API key.

## Setup

Both sides need their own dependencies (the Pi shouldn't install web/LLM stuff it
doesn't need):

**On the Pi:**
```
pip install -r requirements-pi.txt
python detection/detect.py
```

**On the laptop:**
```
pip install -r requirements-laptop.txt
```

Create a `.env` file in the repo root (gitignored, never commit it) with a free
[Google AI Studio](https://aistudio.google.com) key:
```
GEMINI_API_KEY=your_key_here
```

Then:
```
python app.py
```
and open `http://localhost:5000`.

## Pages

| Route | What it does |
|---|---|
| `/` | Tree Dex card grid. Click "Reveal" on any catch to generate (and permanently save) an AI nickname + flavor text for that specific tree. |
| `/planting` | Type a ZIP code, get real climate data + a Gemini planting recommendation for that site. |
| `/map` | Leaflet map of scanned zones (currently sample data), colored by catch density. Click a zone for its planting recommendation. Includes a locust-risk toggle that honestly explains what real data it would need rather than faking a prediction. |
| `/canopy-mapping`, `/health-monitoring`, `/locust-risk` | "Under development" pages describing planned features and what each actually needs to become real. |

## Status

- [x] Detection pipeline (Pi → ONNX → NMS-deduped → `log.csv` + crops)
- [x] Tree Dex front-end, with persistent AI-generated nicknames/flavor text per catch
- [x] Climate-smart planting recommendations (ZIP-based)
- [ ] **GPS-tagged catches** — the current priority. `/planting`'s manual ZIP entry
      and `/map`'s hardcoded sample zones are placeholders for real geotagged data.
      Plan: log GPS from the flight controller's Blackbox during flight, match it to
      Pi detections by timestamp after landing, replace `site_zones.py`'s fake zones
      with real clustered catch locations. Blocked on: verifying Blackbox GPS logging
      works on this specific board, then an actual outdoor test flight.
- [ ] Urban canopy / heat-gap mapping — depends on GPS-tagged catches existing first
- [ ] Tree health monitoring — needs repeated flights over the same site over time
- [ ] Pest/outbreak risk flagging (exploratory) — needs real rainfall-anomaly,
      soil-moisture, NDVI, and historical-observation datasets; not visual bug-spotting

## Data notes

`dex/log.csv` in this repo is sample data from real test flights. The cropped
images themselves (`dex/crops/`) and the trained model (`detection/*.onnx`) are
gitignored since they're large binaries — regenerate them by running `detect.py`,
or ask for a copy of the trained model directly.
