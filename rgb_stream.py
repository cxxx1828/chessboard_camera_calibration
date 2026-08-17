"""
Normal RGB camera stream from RealSense D457, undistorted using calibration .yaml files.
Just a plain color video feed, nothing fancy 

Usage:
    python3 rgb_stream.py

Press Q to quit.
"""

import cv2
import numpy as np
import pyrealsense2 as rs

from common import load_mono_yaml

RGB_INTRINSICS = "results/rgb_intrinsics.yaml"

WIDTH, HEIGHT, FPS = 1280, 720, 30


def main():
    K, dist, _ = load_mono_yaml(RGB_INTRINSICS)

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
    pipeline.start(config)

    print("Q = quit")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            img = np.asanyarray(color_frame.get_data())
            undistorted = cv2.undistort(img, K, dist)

            cv2.imshow("D457 RGB stream", undistorted)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()