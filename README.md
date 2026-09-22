# PassionJuice: Aerial Land Assessment for Climate-Smart Planting

PassionJuice is a self-built 5" quadcopter that surveys land from above and
detects trees in real time. Each detection is tagged with its GPS location from
the flight controller and "caught" into the Tree Dex, a Pokédex-style web
collection where every tree gets an AI-generated nickname and a short fact. The
same data feeds a more serious feature: climate-aware planting recommendations
built from real climate data and Gemini, shown on a live map of where the trees
were found.

The idea is a citizen-science tool in the spirit of iNaturalist and eBird: find
where canopy is missing, then suggest what would actually survive there.

## Impact/Goal: Climate Change

PassionJuice exists to make biodiversity and canopy data collection accessible enough that ordinary people actually want to contribute to it — a "fun front-end, real impact back-end" approach. Every drone-caught, GPS-tagged tree feeds into a pipeline that pulls real climate data for that location (USDA hardiness zone, rainfall and temperature normals) and turns it into a climate-aware planting recommendation via Gemini, weighted toward climate resilience, carbon capture, and native or endangered species. The goal is to close the gap between "where is canopy missing" and "what should actually be planted there" — a citizen-science tool, in the spirit of iNaturalist and eBird, that scales climate-smart reforestation decisions down to the neighborhood level.

Build log (photos, wiring, and everything that went wrong):
[PassionJuice build log](https://docs.google.com/presentation/d/1nEofchMasy27EcYtwU0i3Pb7w4pghgpwYOgNFogjeMs/edit?usp=sharing)

## Hardware

- Frame: QAV250
- Flight controller: SpeedyBee F405 V5
- Motors: T-Motor V2306
- GPS: M8N (wired to the FC's UART4)
- Companion computer: Raspberry Pi Zero 2W + Camera Module V2, powered by a UBEC
  off the main battery and connected to the FC's UART2 over MSP for live telemetry

## How it works

Two machines with two jobs, plus a live wire between the Pi and the flight
controller.

**On the Pi (in the air).** [detection/detect.py](detection/detect.py) runs as a
systemd service that starts on boot and keeps going until power is cut. Each loop
it captures a frame, runs a custom-trained YOLOv8 model (exported to ONNX) with
`onnxruntime`, and uses non-max suppression to collapse overlapping detections.
It reads GPS, altitude, speed, and battery from the FC over MSP (`yamspy`) and
writes each surviving detection to `dex/log.csv` with a cropped image in
`dex/crops/`. Coordinates are logged with the detection, so no post-processing is
needed. If the FC isn't connected, it logs without flight data instead of
blocking. There is no PyTorch and no web stack on the Pi. It only detects, tags,
and logs.

**On the laptop (on the ground).** [app.py](app.py) is a Flask app that reads
`dex/log.csv`, renders the Tree Dex, and hosts the features that need internet
access (climate APIs and Gemini).

```
detection/   Pi side: detection + MSP telemetry script (best.onnx goes here)
deploy/      systemd unit file for auto-starting detect.py on the Pi
scripts/     One-off maintenance utilities (e.g. cleaning up bad detections)
dex/         Catch log (log.csv) and cropped images (crops/), created on first run
assessment/  Climate lookup, Gemini prompts, and GPS matching
app.py       Laptop side: Flask front end and API routes
```

**assessment/ modules**

- `climate.py`: ZIP code to USDA hardiness zone plus rainfall and temperature
  normals (zippopotam.us, phzmapi.org, open-meteo.com, none of which need an API
  key). It also reverse-geocodes lat/lon to a ZIP code (nominatim.openstreetmap.org)
  for the map.
- `recommend.py`: takes a climate profile and catch count and asks Gemini for a
  planting recommendation, weighted toward climate resilience, carbon capture, and
  native or endangered species.
- `flavor.py`: sends a caught tree's photo to Gemini (vision) and gets back a
  structured `{nickname, flavor}`. The species is a visual guess, since the
  detection model has one class ("tree") and no species classifier.
- `geotag.py`: fallback GPS matching. It parses a Blackbox CSV export and matches
  it to catches by timestamp within 60 seconds, and refuses to pair unrelated
  flights. Only needed when a catch has no live coordinates.
- `site_zones.py`: builds map zones from GPS-tagged catches in `log.csv`, and falls
  back to labeled sample zones if there are none yet.
- `test_gemini.py`: standalone check that your Gemini API key works.

## The detection model

The trained model (`detection/best.onnx`) is not in this repo because it is a
large binary, so you need to train your own to run the Pi side. The recipe I used:

1. Dataset: Roboflow Universe `tree-detection-0sywt` (5,855 aerial drone canopy
   images). Delete any stray junk classes so `data.yaml` shows `nc: 1` and
   `names: ['tree']`.
2. Train YOLOv8n in Google Colab (T4 GPU): 100 epochs, `imgsz=640`, `patience=20`.
   Mount Google Drive so a disconnect doesn't lose progress.
3. Export to ONNX. The output shape for one class should be `[1, 5, 8400]`.
4. Save it as `detection/best.onnx`.

## Setup

Each side installs only what it needs, so the Pi stays light.

**On the Pi**

```
pip install -r requirements-pi.txt
python detection/detect.py
```

To run it as a service that starts on every boot:

```
sudo cp deploy/detect.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable detect.service
sudo systemctl start detect.service
```

Edit `User` and the paths in `detect.service` first if your Pi username isn't
`mrdrone`. Check on it with `sudo systemctl status detect.service` or follow the
output with `journalctl -u detect.service -f`. Once enabled it starts on every
boot, and `systemctl stop` only pauses the current run.

If OpenCV crashes with "Bus error" on the Pi Zero 2W, use the system package
instead of the pip one: `sudo apt install python3-opencv`.

**On the laptop**

```
pip install -r requirements-laptop.txt
cp .env.example .env
```

Put a free [Google AI Studio](https://aistudio.google.com) key in `.env`
(gitignored, never commit it), then:

```
python app.py
```

Open `http://localhost:5000`. Set `FLASK_DEBUG=1` if you want Flask's debug mode.

**After a flight**, copy the Pi's data to the laptop before running the app:

```
scp -r <pi-user>@<pi-hostname>.local:~/PassionJuice/dex ./
```

## Pages

| Route | What it does |
|---|---|
| `/` | Tree Dex card grid. Only clear, high-confidence catches show here (a stricter filter than the map uses). "Reveal" generates and saves an AI nickname and fact for a catch, and you can delete a catch. |
| `/planting` | Enter a ZIP code to get real climate data and a Gemini planting recommendation for that site. |
| `/map` | Leaflet map of scanned zones, colored by catch density. It shows real GPS-tagged catches once they exist and labeled sample zones until then; the banner at the top says which. Click a zone for its planting recommendation. The locust-risk toggle explains what real data a prediction would need instead of faking one. |
| `/canopy-mapping`, `/health-monitoring`, `/locust-risk` | "Under development" pages that describe each planned feature and what it needs to become real. |

## Status

- [x] Detection pipeline (Pi, ONNX, deduplicated, `log.csv` and crops)
- [x] Tree Dex front end with saved AI nicknames and facts
- [x] Climate-smart planting recommendations (ZIP based)
- [x] Live GPS-tagged catches read from the FC over MSP. `/map` shows real data as soon as it exists, and `geotag.py` remains as a fallback for older logs.
- [ ] Urban canopy and heat-gap mapping (per-zone clustering of GPS-tagged catches)
- [ ] Tree health monitoring (needs repeated flights over the same site)
- [ ] Pest and outbreak risk flagging (exploratory; needs rainfall-anomaly, soil-moisture, NDVI, and historical-observation datasets, not visual bug-spotting)

## Known issues

- During the first test flight, GPS telemetry stopped partway through the session
  while the camera and detection kept working. The cause is not confirmed. The
  leading suspect is a marginal solder joint that fails under vibration.
- That flight was mostly hovering, so the map data so far is sparse and clustered.
  The map groups nearby catches into zones (25 m by default) so overlapping pins
  don't hide the density.

## Data notes

`dex/log.csv`, the cropped images in `dex/crops/`, and the trained model
(`detection/*.onnx`) are gitignored. The crops and model are large binaries. The
log is excluded because it holds precise GPS coordinates once flights are logged,
which shouldn't be public.

If `detect.py` runs continuously in the background (for example under systemd)
with the camera pointed at nothing, it can log confident but meaningless
detections on dark or blank frames. `scripts/cleanup_blank_catches.py` removes
them by checking each crop's brightness and variance. Run it from the repo root
whenever the log needs a cleanup.

## License

MIT. See [LICENSE](LICENSE).
