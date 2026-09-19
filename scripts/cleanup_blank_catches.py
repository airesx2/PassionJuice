"""
One-off maintenance script: removes catches whose crop image is essentially
blank/black -- e.g. detect.py's systemd service running continuously in the
background while the camera wasn't actually pointed at anything, producing
confident-but-meaningless "tree" detections on near-uniform images.

Thresholds calibrated against a real sample of this project's crops: blank
images measured mean brightness under ~22 and std dev under ~3.1, while real
captures measured well above 54 mean and 5.6 std -- a comfortable gap, so
mean < 30 or std < 4 catches the blanks without touching real photos.

Run from the repo root: python scripts/cleanup_blank_catches.py
"""
import csv
import os
import cv2

LOG_FILE = os.path.join("dex", "log.csv")
CROPS_DIR = os.path.join("dex", "crops")
BRIGHTNESS_THRESHOLD = 30
VARIANCE_THRESHOLD = 4

def is_blank(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return True  # missing/corrupt file counts as junk too
    return img.mean() < BRIGHTNESS_THRESHOLD or img.std() < VARIANCE_THRESHOLD

def main():
    with open(LOG_FILE, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    kept = []
    removed = 0
    for row in rows:
        crop_file = os.path.basename(row.get("crop_file") or "")
        crop_path = os.path.join(CROPS_DIR, crop_file)
        if crop_file and os.path.exists(crop_path) and is_blank(crop_path):
            os.remove(crop_path)
            removed += 1
        else:
            kept.append(row)

    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)

    print(f"Removed {removed} blank/junk catches, kept {len(kept)}")

if __name__ == "__main__":
    main()
