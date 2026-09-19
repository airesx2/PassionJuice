# Tree Dex — Aerial Land Assessment for Climate-Smart Planting

A self-built 5" FPV quadcopter surveys land from above and detects trees/vegetation
in real time, tagging each detection with its real GPS location straight from the
flight controller. Every detection is "caught" into a Pokédex-style web collection
(the fun front-end) — complete with an AI-generated nickname and flavor text for
each tree — while the same catch data quietly feeds a real environmental-impact
feature underneath: climate-aware planting recommendations powered by real climate
data and Gemini, plotted on a live map of where catches actually happened.

## Hardware

- Frame: QAV250
- Flight controller: SpeedyBee F405 V5
- Motors: T-Motor V2306
- GPS: M8N (wired to the FC's UART4)
- Companion computer: Raspberry Pi Zero 2W + Camera Module V2, powered by a UBEC
  off the main battery, connected to the FC's UART2 over MSP for live telemetry
- Build Log [https://docs.google.com/presentation/d/1nEofchMasy27EcYtwU0i3Pb7w4pghgpwYOgNFogjeMs/edit?usp=sharing]

## Architecture

Two machines, two jobs, plus a live wire between the Pi and the flight controller:

- **Pi (weak, in the air)** — [detection/detect.py](detection/detect.py) runs as a
  systemd service that auto-starts on boot and keeps going until power is cut. Each
  loop: captures a frame, runs a custom-trained YOLOv8 model (exported to ONNX) via
  `onnxruntime`, applies Non-Max Suppression to collapse duplicate/overlapping
  detections, reads live GPS/altitude/speed/battery telemetry from the FC over MSP
  (`yamspy`), and logs each surviving detection straight to `dex/log.csv` with a
  cropped image in `dex/crops/` — coordinates included, no post-processing needed.
  If the FC isn't connected/wired, it logs without flight data instead of blocking.
  No PyTorch, no heavy web stack — this box just needs to detect, tag, and log.
- **Laptop (strong, on the ground)** — [app.py](app.py) is a Flask app that reads
  `dex/log.csv`, renders the Tree Dex card grid, and hosts the impact-layer
  features, which need internet access for climate-data APIs and Gemini calls.

```
detection/   Pi-side: model (best.onnx) + detection + MSP telemetry script
deploy/      systemd unit file for auto-starting detect.py on the Pi
scripts/     One-off maintenance utilities (e.g. cleaning up bad detections)
dex/         Shared data: catch log (log.csv) + cropped images (crops/)
assessment/  Impact-layer modules (climate lookup, LLM reasoning, GPS matching)
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
- `geotag.py` — the fallback path for matching catches to GPS: parses a Blackbox
  CSV export and time-matches it to catches within a 60-second tolerance, refusing
  to pair unrelated flights. Only needed if a catch has no live coordinates already.
- `site_zones.py` — builds map zones from real GPS-tagged catches in `log.csv`
  first; only falls back to hardcoded sample zones if none exist yet.
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

**To run it as an auto-starting service instead** (recommended — survives reboots
with no manual step):
```
sudo cp deploy/detect.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable detect.service
sudo systemctl start detect.service
```
Check on it with `sudo systemctl status detect.service` or watch it live with
`journalctl -u detect.service -f`. Once `enable`d, it starts itself on every future
boot automatically — `systemctl stop` only pauses the current run, it doesn't
undo that.

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

**After a real flight**, pull the Pi's data onto the laptop before running the app:
```
scp -r mrdrone@dronepi.local:~/PassionJuice/dex ./
```

## Pages

| Route | What it does |
|---|---|
| `/` | Tree Dex card grid — only clear, high-confidence catches are featured here (a separate, stricter filter than what the map uses, so the collection stays curated). Click "Reveal" to generate (and permanently save) an AI nickname + flavor text for a catch, or delete a catch entirely. |
| `/planting` | Type a ZIP code, get real climate data + a Gemini planting recommendation for that site. |
| `/map` | Leaflet map of scanned zones, colored by catch density. Shows real GPS-matched catches once they exist; falls back to labeled sample zones otherwise — the banner at the top says which one you're looking at. Click a zone for its planting recommendation. Includes a locust-risk toggle that honestly explains what real data it would need rather than faking a prediction. |
| `/canopy-mapping`, `/health-monitoring`, `/locust-risk` | "Under development" pages describing planned features and what each actually needs to become real. |

## Status

- [x] Detection pipeline (Pi → ONNX → NMS-deduped → `log.csv` + crops)
- [x] Tree Dex front-end, with persistent AI-generated nicknames/flavor text per catch
- [x] Climate-smart planting recommendations (ZIP-based)
- [x] **Live GPS-tagged catches** — `detect.py` reads real GPS/altitude/speed/battery
      from the FC over MSP and logs it directly, no post-flight matching needed.
      `/map` automatically shows real data the moment it exists. `geotag.py`'s
      timestamp-matching approach still exists as a fallback for logs recorded
      before this wiring existed.
- [ ] Urban canopy / heat-gap mapping — real per-zone clustering of GPS-tagged
      catches, now that the underlying data exists
- [ ] Tree health monitoring — needs repeated flights over the same site over time
- [ ] Pest/outbreak risk flagging (exploratory) — needs real rainfall-anomaly,
      soil-moisture, NDVI, and historical-observation datasets; not visual bug-spotting

## Data notes

`dex/log.csv`, the cropped images (`dex/crops/`), and the trained model
(`detection/*.onnx`) are all gitignored and not part of this repo. The crops
and model are excluded for being large binaries; the log is excluded because
it holds real, precise GPS coordinates once flights are logged, which
shouldn't be public. Run `detect.py` to regenerate a local log and crops, or
ask for a copy of the trained model directly.

If `detect.py` has been running continuously in the background (e.g. via the
systemd service) without the camera actually pointed at anything, it can log a
lot of confident-but-meaningless detections on blank/dark frames.
`scripts/cleanup_blank_catches.py` removes those automatically by checking each
crop's actual brightness/variance — run it from the repo root whenever the log
needs a sanity pass.
