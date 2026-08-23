#=====RUNS ON PI=====

import cv2
import numpy as np
import onnxruntime as ort
import subprocess, os, csv
from datetime import datetime

CLASSES = ["tree"]
THRESHOLD = 0.1
os.makedirs("dex/crops", exist_ok=True)
LOG_FILE = "dex/log.csv"

subprocess.run(["rpicam-jpeg", "-o", "capture.jpg", "-t", "1000",
                "--width", "640", "--height", "640", "-n"])
img = cv2.imread("capture.jpg")
img_resized = cv2.resize(img, (640, 640))
blob = img_resized.astype(np.float32) / 255.0
blob = blob.transpose(2, 0, 1)[np.newaxis, :]

session = ort.InferenceSession("best_tree.onnx")
input_name = session.get_inputs()[0].name
outputs = session.run(None, {input_name: blob})
preds = outputs[0][0].T
boxes = preds[:, :4]; scores = preds[:, 4:]
class_ids = np.argmax(scores, axis=1)
confidences = np.max(scores, axis=1)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
saved = 0
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp","species","confidence","crop_file"])
for i in range(len(confidences)):
    if confidences[i] > THRESHOLD:
        cx, cy, w, h = boxes[i]
        x1,y1 = max(int(cx-w/2),0), max(int(cy-h/2),0)
        x2,y2 = min(int(cx+w/2),640), min(int(cy+h/2),640)
        crop = img_resized[y1:y2, x1:x2]
        if crop.size == 0: continue
        crop_name = f"dex/crops/tree_{timestamp}_{saved}.jpg"
        cv2.imwrite(crop_name, crop)
        with open(LOG_FILE,"a",newline="") as f:
            csv.writer(f).writerow([timestamp,"tree",f"{confidences[i]:.2f}",crop_name])
        saved += 1
print(f"Caught {saved} trees")