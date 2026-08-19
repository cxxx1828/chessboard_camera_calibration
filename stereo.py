import sys
import os
import glob
import cv2

from common import (
    find_chessboard,
    refine_corners,
    build_object_points,
    load_mono_yaml,
    save_stereo_yaml,
)

COLS_INNER = 9
ROWS_INNER = 6
SQUARE_SIZE_MM = 29.0

RGB_DIR = "calib_images/rgb"
LEFT_DIR = "calib_images/left_ir"
RIGHT_DIR = "calib_images/right_ir"

RGB_INTRINSICS = "results/rgb_intrinsics.yaml"
LEFT_INTRINSICS = "results/left_ir_intrinsics.yaml"
RIGHT_INTRINSICS = "results/right_ir_intrinsics.yaml"

PAIRS = {
    "left-right": {
        "dir1": LEFT_DIR,
        "dir2": RIGHT_DIR,
        "intrinsics1": LEFT_INTRINSICS,
        "intrinsics2": RIGHT_INTRINSICS,
        "gray1": lambda f: cv2.imread(f, cv2.IMREAD_GRAYSCALE),
        "gray2": lambda f: cv2.imread(f, cv2.IMREAD_GRAYSCALE),
        "out_file": "results/stereo_left_right.yaml",
        "label": "left IR <-> right IR",
    },
    "rgb-left": {
        "dir1": RGB_DIR,
        "dir2": LEFT_DIR,
        "intrinsics1": RGB_INTRINSICS,
        "intrinsics2": LEFT_INTRINSICS,
        "gray1": lambda f: cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2GRAY),
        "gray2": lambda f: cv2.imread(f, cv2.IMREAD_GRAYSCALE),
        "out_file": "results/stereo_rgb_left.yaml",
        "label": "RGB <-> left IR",
    },
}


def calibrate(pair_name):
    cfg = PAIRS[pair_name]

    if not os.path.exists(cfg["intrinsics1"]) or not os.path.exists(cfg["intrinsics2"]):
        print(f"Missing mono intrinsics for {cfg['label']}. Run the relevant *_mono.py calibrate first.")
        return

    K1, dist1, _ = load_mono_yaml(cfg["intrinsics1"])
    K2, dist2, _ = load_mono_yaml(cfg["intrinsics2"])

    images1 = sorted(glob.glob(os.path.join(cfg["dir1"], "*.png")))

    objp = build_object_points(COLS_INNER, ROWS_INNER, SQUARE_SIZE_MM)

    objpoints = []
    imgpoints1 = []
    imgpoints2 = []
    img_shape = None

    used = 0
    for f1 in images1:
        basename = os.path.basename(f1)
        f2 = os.path.join(cfg["dir2"], basename)
        if not os.path.exists(f2):
            print(f"Skipping {basename} (no matching frame in {cfg['dir2']})")
            continue

        gray1 = cfg["gray1"](f1)
        gray2 = cfg["gray2"](f2)
        img_shape = gray1.shape[::-1]

        found1, corners1 = find_chessboard(gray1, COLS_INNER, ROWS_INNER)
        found2, corners2 = find_chessboard(gray2, COLS_INNER, ROWS_INNER)

        if not (found1 and found2):
            print(f"Skipping {basename} (chessboard not found in both frames)")
            continue

        corners1 = refine_corners(gray1, corners1)
        corners2 = refine_corners(gray2, corners2)

        objpoints.append(objp)
        imgpoints1.append(corners1)
        imgpoints2.append(corners2)
        used += 1

    if used < 5:
        print("Not enough valid synchronized pairs for stereo calibration.")
        return

    print(f"Computing stereo calibration ({cfg['label']}) from {used} synchronized pairs...")

    flags = cv2.CALIB_FIX_INTRINSIC
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-5)

    ret, K1, dist1, K2, dist2, R, T, E, F = cv2.stereoCalibrate(
        objpoints,
        imgpoints1,
        imgpoints2,
        K1,
        dist1,
        K2,
        dist2,
        img_shape,
        criteria=criteria,
        flags=flags,
    )

    print(f"\n=== RESULT ({cfg['label']}) ===")
    print(f"RMS reprojection error: {ret:.4f} px")
    print("Rotation R:\n", R)
    print("Translation T (mm):\n", T)

    baseline_mm = cv2.norm(T)
    print(f"Baseline: {baseline_mm:.2f} mm")

    out_file = cfg["out_file"]
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    save_stereo_yaml(out_file, K1, dist1, K2, dist2, R, T, E, F, ret)
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 2 or args[0] != "calibrate" or args[1] not in PAIRS:
        print(__doc__)
        sys.exit(1)

    calibrate(args[1])

