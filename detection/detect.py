#=====RUNS ON PI=====

import cv2
import numpy as np
import onnxruntime as ort #runs my exported model
import subprocess, os, csv, signal, time #launch Pi's camera tool first and wait to finish
from datetime import datetime

try:
    from yamspy import MSPy
except ImportError:
    MSPy = None  # FC telemetry becomes optional -- bench tests without the FC wired up still work

CLASSES = ["tree"] #detect tree
THRESHOLD = 0.1 #10% confidence level to count
#decr if seeing dupes
#inc if missing trees
NMS_THRESHOLD = 0.4 #40% overlap to count as dupe

CAPTURE_INTERVAL = 3   # seconds to wait between photos during a survey

FC_SERIAL_PORT = "/dev/serial0"  # spare FC UART wired to the Pi's GPIO14/15, set to "MSP" in Betaflight
FC_BAUDRATE = 115200              # must match whatever's set for that UART in Betaflight's Ports tab

# Runs until power is cut or the service is stopped -- no fixed duration.
# systemd sends SIGTERM to stop a service (not SIGINT/Ctrl+C), so both need
# to be caught the same way for this to shut down cleanly either way.
running = True

def _handle_stop_signal(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, _handle_stop_signal)
signal.signal(signal.SIGINT, _handle_stop_signal)

# Resolve paths relative to the repo root (one level above this file),
# so this script works no matter what directory it's launched from
# (matters once this runs as a cron job / systemd service on the Pi).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEX_DIR = os.path.join(BASE_DIR, "dex")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.onnx")

os.makedirs(os.path.join(DEX_DIR, "crops"), exist_ok=True) #creates dex/crop folder if missing
LOG_FILE = os.path.join(DEX_DIR, "log.csv")

# Full column set. nickname/flavor are filled in later by the web app's
# Reveal feature, not by this script -- they're included here so the
# header is right from the start and nothing needs to migrate later.
FIELDNAMES = [
    "timestamp", "species", "confidence", "crop_file", "nickname", "flavor",
    "latitude", "longitude", "satellites", "gps_altitude_m",
    "ground_speed_ms", "battery_voltage",
]

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()

# Load the model once, outside the loop -- reused for every capture during
# the survey instead of being reloaded (slow) each time.
session = ort.InferenceSession(MODEL_PATH)
input_name = session.get_inputs()[0].name


def read_flight_data(board):
    """Best-effort read of GPS + battery telemetry from the FC over MSP.
    Deliberately never raises -- a bad read here should mean this one
    photo just has no flight data attached, not that the whole survey
    crashes because of a flaky serial link mid-flight."""
    data = {
        "latitude": None, "longitude": None, "satellites": None,
        "gps_altitude_m": None, "ground_speed_ms": None, "battery_voltage": None,
    }
    if board is None:
        return data

    try:
        if board.send_RAW_msg(MSPy.MSPCodes["MSP_RAW_GPS"], data=[]):
            board.process_recv_data(board.receive_msg())
            gps = board.GPS_DATA
            if gps["fix"] and gps["numSat"] > 0:
                data["latitude"] = gps["lat"] / 1e7          # MSP sends degrees x 1e7
                data["longitude"] = gps["lon"] / 1e7
                data["satellites"] = gps["numSat"]
                data["gps_altitude_m"] = gps["alt"]
                data["ground_speed_ms"] = gps["speed"] / 100  # MSP sends cm/s
    except Exception:
        pass  # any comms hiccup just means no GPS for this one photo

    try:
        board.fast_read_analog()
        data["battery_voltage"] = board.ANALOG.get("voltage")
    except Exception:
        pass

    return data


def capture_and_detect(board=None):
    """Takes one photo, runs detection + NMS, saves any surviving crops
    tagged with whatever flight data the FC provided at that moment.
    Returns how many trees were saved from this one photo."""
    #run pi camera cli tool
    #-t 1000 = 1 second delay before capture
    #--width/ --height 640 matches model input size
    #-n skip preview window (for headless pi)
    subprocess.run(["rpicam-jpeg", "-o", "capture.jpg", "-t", "1000",
                    "--width", "640", "--height", "640", "-n"])
    img = cv2.imread("capture.jpg")
    img_resized = cv2.resize(img, (640, 640))
    blob = img_resized.astype(np.float32) / 255.0 #pixel ints 0-255; model expect float normalize 0-1
    blob = blob.transpose(2, 0, 1)[np.newaxis, :]
    #OpenCV expect h,w,c; ML model expect c,h,w
    #[np.newaxis, :] adds a batch dimension (1,3,640,640) for model input

    outputs = session.run(None, {input_name: blob})
    preds = outputs[0][0].T
    boxes = preds[:, :4]; scores = preds[:, 4:]
    confidences = np.max(scores, axis=1) #actual highest score per row

    #PASS1: collect boxes above threshold
    boxes_for_nms = []
    scores_for_nms = []
    for i in range(len(confidences)):
        if confidences[i] > THRESHOLD:
            cx, cy, w, h = boxes[i]
            x = int(cx - w / 2); y = int(cy - h / 2)
            boxes_for_nms.append([x, y, int(w), int(h)])
            scores_for_nms.append(float(confidences[i]))

    #PASS2: suppress overlapping boxes (non-max suppression)
    keep_indices = cv2.dnn.NMSBoxes(boxes_for_nms, scores_for_nms, THRESHOLD, NMS_THRESHOLD)
    keep_indices = np.array(keep_indices).flatten() if len(keep_indices) > 0 else [] #deals with empty case if needed

    if len(keep_indices) == 0:
        return 0

    # One flight-data read per photo, not per tree -- position barely
    # changes within the same instant, and it's one less MSP round-trip.
    flight_data = read_flight_data(board)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = 0
    #PASS3: crop + save survived NMS
    for i in keep_indices:
        x, y, w, h = boxes_for_nms[i]
        x1, y1 = max(int(x), 0), max(int(y), 0)
        x2, y2 = min(int(x + w), 640), min(int(y + h), 640)
        crop = img_resized[y1:y2, x1:x2] #numpy array slice [rows, cols] = [y, x]
        if crop.size == 0: continue #guard against empty crop
        crop_name = os.path.join(DEX_DIR, "crops", f"tree_{timestamp}_{saved}.jpg")
        cv2.imwrite(crop_name, crop)
        row = {
            "timestamp": timestamp,
            "species": "tree",
            "confidence": f"{scores_for_nms[i]:.2f}",
            "crop_file": crop_name,
            **flight_data,
        }
        with open(LOG_FILE, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES, restval="").writerow(row)
        saved += 1
    return saved


if __name__ == "__main__":
    print(f"Starting survey: capturing every {CAPTURE_INTERVAL}s until stopped (Ctrl+C or shutdown)...")

    board = None
    if MSPy is not None:
        try:
            board = MSPy(device=FC_SERIAL_PORT, loglevel="WARNING", baudrate=FC_BAUDRATE).__enter__()
            print(f"Connected to FC over MSP on {FC_SERIAL_PORT}")
        except Exception as e:
            print(f"No FC connection ({e}) -- continuing without flight data")
    else:
        print("yamspy not installed -- continuing without flight data")

    total_saved = 0
    try:
        while running:
            total_saved += capture_and_detect(board)
            time.sleep(CAPTURE_INTERVAL)
    finally:
        if board is not None:
            board.__exit__(None, None, None)
    print(f"Caught {total_saved} trees this survey")
