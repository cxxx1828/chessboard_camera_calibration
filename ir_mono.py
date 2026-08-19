"""
Mono calibration for RealSense D457 IR sensors (left + right) using a 9x6 chessboard, 29mm squares.

Usage:
    python3 ir_mono.py calibrate left  -> compute calibration for the left IR sensor
    python3 ir_mono.py calibrate right -> compute calibration for the right IR sensor

Results are saved to ./results/left_ir_intrinsics.yaml and ./results/right_ir_intrinsics.yaml

Note: capture.py disables the IR emitter (laser projector) during capture,
since its dot pattern interferes with chessboard corner detection.
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

LEFT_IMG_DIR = "calib_images/left_ir"
RIGHT_IMG_DIR = "calib_images/right_ir"

RESULTS = {
    "left": ("calib_images/left_ir", "results/left_ir_intrinsics.yaml"),
    "right": ("calib_images/right_ir", "results/right_ir_intrinsics.yaml"),
}


def calibrate(side):
    img_dir, out_file = RESULTS[side]
    images = sorted(glob.glob(os.path.join(img_dir, "*.png")))
    if len(images) < 10:
        print(f"Warning: only {len(images)} images, recommended minimum is 15-20 with varied angles/distances.")

    objp = build_object_points(COLS_INNER, ROWS_INNER, SQUARE_SIZE_MM)

    objpoints = []
    imgpoints = []
    img_shape = None

    used = 0
    for fname in images:
        gray = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
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

    print(f"Computing {side} IR calibration from {used} images...")
    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, img_shape, None, None
    )

    print(f"\n=== RESULT ({side} IR) ===")
    print(f"RMS reprojection error: {ret:.4f} px")
    print("Camera matrix K:\n", K)
    print("Distortion coeffs:\n", dist)

    errors = calculate_reprojection_error(objpoints, imgpoints, rvecs, tvecs, K, dist)
    for fname, err in zip(images, errors):
        print(f"  {os.path.basename(fname)}: {err:.4f} px")

    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    save_mono_yaml(out_file, img_shape, K, dist, ret)
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) == 2 and args[0] == "calibrate" and args[1] in ("left", "right"):
        calibrate(args[1])
    else:
        print(__doc__)
        sys.exit(1)