"""
Combined stereo depth view for RealSense D457, computed from your own
calibration (not the camera's built-in depth). Fuses left+right IR into
a single colorized disparity/depth image.

Usage:
    python3 depth_view.py

Press Q to quit.
"""

import cv2
import numpy as np
import pyrealsense2 as rs

from common import load_mono_yaml

LEFT_INTRINSICS = "results/left_ir_intrinsics.yaml"
RIGHT_INTRINSICS = "results/right_ir_intrinsics.yaml"
STEREO_LEFT_RIGHT = "results/stereo_left_right.yaml"

WIDTH, HEIGHT, FPS = 1280, 720, 30


def load_stereo_yaml(path):
    fs = cv2.FileStorage(path, cv2.FILE_STORAGE_READ)
    R = fs.getNode("R").mat()
    T = fs.getNode("T").mat()
    fs.release()
    return R, T


def main():
    K_left, dist_left, img_size = load_mono_yaml(LEFT_INTRINSICS)
    K_right, dist_right, _ = load_mono_yaml(RIGHT_INTRINSICS)
    R, T = load_stereo_yaml(STEREO_LEFT_RIGHT)

    R1, R2, P1, P2, _, _, _ = cv2.stereoRectify(
        K_left, dist_left, K_right, dist_right, img_size, R, T,
        flags=cv2.CALIB_ZERO_DISPARITY, alpha=0,
    )
    map1_l, map2_l = cv2.initUndistortRectifyMap(K_left, dist_left, R1, P1, img_size, cv2.CV_16SC2)
    map1_r, map2_r = cv2.initUndistortRectifyMap(K_right, dist_right, R2, P2, img_size, cv2.CV_16SC2)

    # Stereo matcher: converts left/right rectified pair into one disparity image
    num_disparities = 16 * 8   # must be divisible by 16
    block_size = 7
    stereo = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=num_disparities,
        blockSize=block_size,
        P1=8 * 1 * block_size ** 2,
        P2=32 * 1 * block_size ** 2,
        disp12MaxDiff=1,
        uniquenessRatio=10,
        speckleWindowSize=100,
        speckleRange=2,
    )

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.infrared, 1, WIDTH, HEIGHT, rs.format.y8, FPS)
    config.enable_stream(rs.stream.infrared, 2, WIDTH, HEIGHT, rs.format.y8, FPS)
    profile = pipeline.start(config)

    depth_sensor = profile.get_device().first_depth_sensor()
    if depth_sensor.supports(rs.option.emitter_enabled):
        depth_sensor.set_option(rs.option.emitter_enabled, 1)  # emitter ON helps stereo matching on flat surfaces

    print("Q = quit")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            left_frame = frames.get_infrared_frame(1)
            right_frame = frames.get_infrared_frame(2)
            if not (left_frame and right_frame):
                continue

            left = np.asanyarray(left_frame.get_data())
            right = np.asanyarray(right_frame.get_data())

            left_rect = cv2.remap(left, map1_l, map2_l, cv2.INTER_LINEAR)
            right_rect = cv2.remap(right, map1_r, map2_r, cv2.INTER_LINEAR)

            disparity = stereo.compute(left_rect, right_rect).astype(np.float32) / 16.0

            # normalize for display and apply a color map (JET: near=red/warm, far=blue/cool)
            disp_norm = cv2.normalize(disparity, None, 0, 255, cv2.NORM_MINMAX)
            disp_norm = disp_norm.astype(np.uint8)
            disp_color = cv2.applyColorMap(disp_norm, cv2.COLORMAP_JET)

            cv2.imshow("Stereo depth (from your calibration)", disp_color)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()