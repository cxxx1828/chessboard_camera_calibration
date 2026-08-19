# RealSense D455/D457 Chessboard Calibration

Calibration of the RGB, left IR, and right IR sensors on an Intel RealSense
D455/D457 camera, using a classic chessboard as the calibration target.

> This is the chessboard variant of the pipeline. An AprilGrid variant also
> exists (more precise detection, more robust to a partially occluded board) —
> if you need that version instead, let me know.

## Calibration board

- **9 × 6** inner corners (10×7 squares)
- Square size: **29 mm**
- Standard printed chessboard; must match `COLS_INNER`, `ROWS_INNER`,
  `SQUARE_SIZE_MM` in the code

> The board must be **perfectly flat** (mounted on a rigid backing, not a
> loose sheet of paper) — `cv2.findChessboardCorners` is sensitive to plane
> deformation, far more so than the AprilGrid approach.

## Project structure

```
chessboard_calibration/
├── capture.py          # synchronized RGB + IR1 + IR2 image capture
├── common.py             # shared helper functions (detection, YAML I/O)
├── rgb_mono.py            # mono calibration of the RGB sensor
├── ir_mono.py             # mono calibration of the left/right IR sensor
├── stereo.py              # stereo calibration (left-right, rgb-left)
├── calib_images/
│   ├── rgb/
│   ├── left_ir/
│   └── right_ir/
└── results/
    ├── rgb_intrinsics.yaml
    ├── left_ir_intrinsics.yaml
    ├── right_ir_intrinsics.yaml
    ├── stereo_left_right.yaml
    └── stereo_rgb_left.yaml
```

## Dependencies

```bash
pip3 install pyrealsense2 opencv-python numpy
```

(`opencv-python` is sufficient here — unlike the AprilGrid variant, the
`cv2.aruco` module isn't needed.)

## Step-by-step order

### 1. Capturing images

```bash
python3 capture.py
```

- `SPACE` — saves a synchronized triplet (RGB + IR1 + IR2), only if the
  chessboard was detected in all three frames
- `Q` — quit
- The IR emitter (laser projector) is automatically disabled during capture,
  since its dot pattern interferes with chessboard corner detection
- Recommendation: capture 15–20+ images (ideally more, 40–60) with varied
  angles, distances, and board positions in the frame, including the edges
  and corners of the image

**Resolution/FPS** (`WIDTH, HEIGHT, FPS` at the top of the file) must match
what your USB connection supports:

- USB3 connection: `1280, 720, 30` works for all three streams simultaneously
- USB2 connection: the camera restricts combinations (Color maxes out around
  ~15Hz at 720p, IR around ~5Hz); check `rs-enumerate-devices -c` and use
  `640, 480, 30` if needed

> **Critical**: don't change resolution between captures into the same
> `calib_images/` folder. Mixing resolutions in the same image set silently
> introduces a systematic error into the calibration (RMS jumps 2–4×) with no
> runtime error at all. If you change resolution, delete the old images and
> recapture the whole set from scratch:
> ```bash
> rm -rf calib_images/rgb calib_images/left_ir calib_images/right_ir
> ```

### 2. Mono calibration (must run before the stereo step)

```bash
python3 rgb_mono.py calibrate
python3 ir_mono.py calibrate left
python3 ir_mono.py calibrate right
```

Each command:
- detects the chessboard via `cv2.findChessboardCorners`, then refines it to
  sub-pixel accuracy with `cv2.cornerSubPix`
- computes `cv2.calibrateCamera` (K, distortion coefficients)
- prints the RMS reprojection error for the whole set and per image
- saves the result to `results/*_intrinsics.yaml`

**`stereo.py` reads these `.yaml` files from disk** — it does not recompute
intrinsics on the fly. If you recapture images (a new `capture.py` run), you
must rerun all three mono commands before the stereo step, otherwise stereo
calibration will use stale intrinsics from the old image set.

### 3. Stereo calibration

```bash
python3 stereo.py calibrate left-right
python3 stereo.py calibrate rgb-left
```

- Uses `cv2.CALIB_FIX_INTRINSIC` — mono intrinsics are held fixed, only the
  relative rotation/translation (R, T) between the two sensors is solved for
- For each image pair, requires the chessboard to be detected in BOTH sensors
  simultaneously (`found1 and found2`); otherwise the pair is skipped
- The result (K1, dist1, K2, dist2, R, T, E, F) is saved to
  `results/stereo_*.yaml`

## Expected results (rule of thumb)

| RMS reprojection error | Quality |
|---|---|
| < 0.5 px | excellent, suitable for precise depth/3D |
| 0.5 – 1.5 px | solid, standard for robotics (navigation, docking) |
| > 2–3 px | problematic — check for mixed resolutions, poor focus, or a warped board |

The RGB sensor usually has a higher RMS than the IR sensors (larger factory
distortion), and `stereo_rgb_left` usually comes out somewhat worse than
`stereo_left_right` (two different sensor types instead of an identical
pair) — that's expected, not a bug.

## Parameters that must be changed together

`COLS_INNER`, `ROWS_INNER`, `SQUARE_SIZE_MM` are defined identically in
`ir_mono.py`, `rgb_mono.py`, and `stereo.py` (and `capture.py` has its own
`COLS_INNER`/`ROWS_INNER` that must also match). If you change the board
(different square size or number of squares), these values must be kept in
sync across all files.

## Limitations compared to the AprilGrid approach

- The chessboard must be **fully visible** to be detected — a single
  occluded corner discards the whole frame. AprilGrid detects individual
  tags independently, so a partially occluded board still yields usable data.
- Detection is more sensitive to viewing angle, glare, and warping.
- No built-in ID system — can't distinguish orientation/section of the board
  if only part of it is in frame.

## Troubleshooting

- **`Couldn't resolve requests`** in `capture.py` — the requested
  resolution/FPS combination isn't supported on the current USB connection;
  check `rs-enumerate-devices -c` and adjust `WIDTH, HEIGHT, FPS`
- **`ModuleNotFoundError: pyrealsense2`** — not installed in the active
  virtualenv (`pip3 install pyrealsense2`)
- **Sudden jump in RMS after adding new images** — almost always mixed
  resolutions in the same folder; delete and recapture at a single resolution
- **`stereo.py` reports an unrealistically high RMS even though the mono
  results look good** — check whether you ran the mono calibrations on the
  CURRENT image set before the stereo step (see step 2)
- **Many rejected frames ("chessboard not found")** — check lighting, focus,
  and whether the board is flat enough; chessboards are less tolerant of
  these factors than AprilGrid
