"""
Synchronized calibration image capture for RealSense D457.
Captures RGB, left IR, and right IR from the same frameset.

Usage:
    python3 capture.py

SPACE = save synchronized triplet, Q = quit
Images saved to calib_images/{rgb,left_ir,right_ir}/
"""

import os
import glob
import cv2
import numpy as np
import pyrealsense2 as rs

from common import find_chessboard

COLS_INNER = 9
ROWS_INNER = 6

RGB_DIR = "calib_images/rgb"
LEFT_DIR = "calib_images/left_ir"
RIGHT_DIR = "calib_images/right_ir"

WIDTH, HEIGHT, FPS = 1280, 720, 30


def capture():
    for d in (RGB_DIR, LEFT_DIR, RIGHT_DIR):
        os.makedirs(d, exist_ok=True)

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
    config.enable_stream(rs.stream.infrared, 1, WIDTH, HEIGHT, rs.format.y8, FPS)
    config.enable_stream(rs.stream.infrared, 2, WIDTH, HEIGHT, rs.format.y8, FPS)
    profile = pipeline.start(config)

    depth_sensor = profile.get_device().first_depth_sensor()
    if depth_sensor.supports(rs.option.emitter_enabled):
        depth_sensor.set_option(rs.option.emitter_enabled, 0)

    count = len(glob.glob(os.path.join(RGB_DIR, "*.png")))
    print("SPACE = save synchronized triplet, Q = quit")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            left_frame = frames.get_infrared_frame(1)
            right_frame = frames.get_infrared_frame(2)
            if not (color_frame and left_frame and right_frame):
                continue

            rgb = np.asanyarray(color_frame.get_data())
            left = np.asanyarray(left_frame.get_data())
            right = np.asanyarray(right_frame.get_data())

            found_rgb, corners_rgb = find_chessboard(cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY), COLS_INNER, ROWS_INNER)
            found_left, corners_left = find_chessboard(left, COLS_INNER, ROWS_INNER)
            found_right, corners_right = find_chessboard(right, COLS_INNER, ROWS_INNER)

            disp_rgb = rgb.copy()
            disp_left = cv2.cvtColor(left, cv2.COLOR_GRAY2BGR)
            disp_right = cv2.cvtColor(right, cv2.COLOR_GRAY2BGR)
            for disp, found, corners in (
                (disp_rgb, found_rgb, corners_rgb),
                (disp_left, found_left, corners_left),
                (disp_right, found_right, corners_right),
            ):
                if found:
                    cv2.drawChessboardCorners(disp, (COLS_INNER, ROWS_INNER), corners, found)

            small = [cv2.resize(d, (640, 360)) for d in (disp_rgb, disp_left, disp_right)]
            top = cv2.hconcat(small[:2])
            bottom = cv2.hconcat([small[2], np.zeros_like(small[2])])
            combined = cv2.vconcat([top, bottom])

            labels = [("RGB", found_rgb, (20, 30)), ("LEFT", found_left, (660, 30)), ("RIGHT", found_right, (20, 390))]
            for text, ok, pos in labels:
                color = (0, 255, 0) if ok else (0, 0, 255)
                cv2.putText(combined, f"{text}: {'OK' if ok else 'NO'}", pos, cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            cv2.imshow("D457 calibration capture", combined)
            key = cv2.waitKey(1) & 0xFF

            if key == ord(" "):
                if found_rgb and found_left and found_right:
                    basename = f"img_{count:03d}.png"
                    cv2.imwrite(os.path.join(RGB_DIR, basename), rgb)
                    cv2.imwrite(os.path.join(LEFT_DIR, basename), left)
                    cv2.imwrite(os.path.join(RIGHT_DIR, basename), right)
                    print(f"Saved synchronized frame {count:03d}")
                    count += 1
                else:
                    print("Frame rejected: chessboard must be detected in RGB + LEFT + RIGHT.")
            elif key == ord("q"):
                break
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    capture()