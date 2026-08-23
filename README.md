# Tree Dex — Aerial Land Assessment for Climate-Smart Planting

A self-built 5" FPV quadcopter surveys land from above and detects trees/vegetation
in real time. Every detection is "caught" into a Pokédex-style web collection (the
fun front-end), while the same data quietly feeds a real environmental-impact
feature underneath (the serious back-end).

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
  and logs each detection above threshold to `dex/log.csv` with a cropped image in
  `dex/crops/`. No PyTorch, no heavy web stack — this box just needs to detect and log.
- **Laptop (strong, on the ground)** — [app.py](app.py) is a Flask app that reads
  `dex/log.csv` and renders the Tree Dex card grid. This is also where the
  climate-smart planting feature (in progress) will live, since it needs internet
  access for climate-data lookups and LLM reasoning.

```
detection/   Pi-side: model + detection script
dex/         Shared data: catch log (log.csv) + cropped images (crops/)
assessment/  Impact-layer work in progress (canopy zoning, climate reasoning)
app.py       Laptop-side: Flask front-end
```

## Running it

**On the Pi** (one-time setup, then run per flight/session):

```
pip install -r requirements-pi.txt
python detection/detect.py
```

**On the laptop:**

```
pip install -r requirements-laptop.txt
python app.py
```

Then open `http://localhost:5000`.

## Status

- [x] Detection pipeline (Pi → ONNX → log.csv + crops)
- [x] Tree Dex front-end (Flask card grid)
- [ ] Climate-smart planting recommendations (impact layer, in progress)

## Data notes

`dex/log.csv` in this repo is sample data from real test flights. The cropped
images themselves (`dex/crops/`) and the trained model (`detection/*.onnx`) are
gitignored since they're large binaries — regenerate them by running `detect.py`,
or ask for a copy of the trained model directly.
