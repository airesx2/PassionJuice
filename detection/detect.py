#=====RUNS ON PI=====

import cv2
import numpy as np
import onnxruntime as ort #runs my exported model
import subprocess, os, csv, time #launch Pi's camera tool first and wait to finish
from datetime import datetime

CLASSES = ["tree"] #detect tree
THRESHOLD = 0.1 #10% confidence level to count
#decr if seeing dupes
#inc if missing trees
NMS_THRESHOLD = 0.4 #40% overlap to count as dupe

CAPTURE_INTERVAL = 3   # seconds to wait between photos during a survey
FLIGHT_DURATION = 120  # total seconds to keep detecting before stopping automatically

# Resolve paths relative to the repo root (one level above this file),
# so this script works no matter what directory it's launched from
# (matters once this runs as a cron job / systemd service on the Pi).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEX_DIR = os.path.join(BASE_DIR, "dex")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.onnx")

os.makedirs(os.path.join(DEX_DIR, "crops"), exist_ok=True) #creates dex/crop folder if missing
LOG_FILE = os.path.join(DEX_DIR, "log.csv")

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp","species","confidence","crop_file"])

# Load the model once, outside the loop -- reused for every capture during
# the survey instead of being reloaded (slow) each time.
session = ort.InferenceSession(MODEL_PATH)
input_name = session.get_inputs()[0].name


def capture_and_detect():
    """Takes one photo, runs detection + NMS, saves any surviving crops.
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
        with open(LOG_FILE, "a", newline="") as f:
            csv.writer(f).writerow([timestamp, "tree", f"{scores_for_nms[i]:.2f}", crop_name])
        saved += 1
    return saved


if __name__ == "__main__":
    print(f"Starting survey: capturing every {CAPTURE_INTERVAL}s for up to {FLIGHT_DURATION}s (Ctrl+C to stop early)...")
    start_time = time.time()
    total_saved = 0
    try:
        while time.time() - start_time < FLIGHT_DURATION:
            total_saved += capture_and_detect()
            time.sleep(CAPTURE_INTERVAL)
    except KeyboardInterrupt:
        print("Stopped early.")
    print(f"Caught {total_saved} trees this survey")
