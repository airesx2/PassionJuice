import cv2

img = cv2.imread("")
height, width = img.shape[:2]

grid_size = 6 #6x6=36 zones (change this for finer zones!!)
cell_h = height // grid_size
cell_w = width // grid_size

print(f"Image is {width}x{height}, each zone is ~{cell_w}x{cell_h} px")