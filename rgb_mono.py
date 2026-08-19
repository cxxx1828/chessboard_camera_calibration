"""
Mono calibration for RealSense D457 (RGB stream) using a 9x6 chessboard, 29mm squares.

Usage:
    python3 rgb_mono.py calibrate -> compute calibration from captured images

Result is saved to ./results/rgb_intrinsics.yaml
"""

import sys
import os
import glob
import cv2
import numpy as np

from common import (
    find_chessboard,
    refine_corners,
    build_object_points,
    calculate_reprojection_error,
    save_mono_yaml,
)

# ---- Chessboard parameters (must match the generated PDF board) ----
COLS_INNER = 9      # inner corners across width
ROWS_INNER = 6      # inner corners across height
SQUARE_SIZE_MM = 29.0

IMG_DIR = "calib_images/rgb"
OUT_FILE = "results/rgb_intrinsics.yaml"

def calibrate():
    images = sorted(glob.glob(os.path.join(IMG_DIR, "*.png")))
    if len(images) < 10:
        print(f"Warning: only {len(images)} images, recommended minimum is 15-20 with varied angles/distances.")

    objp = build_object_points(COLS_INNER, ROWS_INNER, SQUARE_SIZE_MM)

    objpoints = []
    imgpoints = []
    img_shape = None

    used = 0
    for fname in images:
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_shape = gray.shape[::-1]

        found, corners = find_chessboard(gray, COLS_INNER, ROWS_INNER)
        if not found:
            print(f"Skipping {fname} (chessboard not found)")
            continue

        corners_refined = refine_corners(gray, corners)
        objpoints.append(objp)
        imgpoints.append(corners_refined)
        used += 1

    if used < 5:
        print("Not enough valid images for calibration.")
        return

    print(f"Computing calibration from {used} images...")
    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, img_shape, None, None
    )

    print("\n=== RESULT ===")
    print(f"RMS reprojection error: {ret:.4f} px")
    print("Camera matrix K:\n", K)
    print("Distortion coeffs:\n", dist)

    # per-image reprojection error (to spot bad samples)
    errors = calculate_reprojection_error(objpoints, imgpoints, rvecs, tvecs, K, dist)
    for fname, err in zip(images, errors):
        print(f"  {os.path.basename(fname)}: {err:.4f} px")

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    save_mono_yaml(OUT_FILE, img_shape, K, dist, ret)
    print(f"\nSaved to {OUT_FILE}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] != "calibrate":
        print(__doc__)
        sys.exit(1)

    calibrate()