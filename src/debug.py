from squidgamesdoll.display import (
    add_camera_settings,
    draw_visor_at_coord,
    draw_target_at_coord,
    ExclusionRect,
    add_exclusion_rectangles,
)
from squidgamesdoll.tracker import TrackerControl
from squidgamesdoll.laser_finder import LaserFinder
from squidgamesdoll.camera import Camera
from time import sleep
from squidgamesdoll.calibration import Calibrator

import cv2

target = ()

rect = ExclusionRect()
rectangles = []


def click_event(event, x, y, flags, param):
    global target, rect, rectangles
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Click registered at ({x}, {y})")
        target = (x, y)
    if event == cv2.EVENT_RBUTTONDOWN:
        if rect.top_left == ExclusionRect.UNDEFINED:
            rect.top_left = (x, y)
        else:
            rect.bottom_right = (x, y)
            rectangles.append(rect)
            rect = ExclusionRect()
            print(f"Added 1 exclusion rectangle")


def point_and_shoot():
    global rectangles
    WINDOW_NAME = "OpenCV"

    index = Camera.getCameraIndex()

    if index == -1:
        print("No compatible webcam found")
        return

    camera = Camera(index)
    camera.auto_exposure()

    cpt = 0

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)  # Create the window outside the loop
    cv2.setMouseCallback(WINDOW_NAME, click_event)  # Set mouse callback once

    finder = LaserFinder()
    tracker = TrackerControl("192.168.2.11", 10, 5)

    coeffs = (20.0, 5.0)
    calibrator = Calibrator(camera, finder, tracker)
    # if calibrator.calibrate():
    #    coeffs = (calibrator.px_per_angle_h, calibrator.px_per_angle_v)
    DEBUG = True

    while True:
        cpt += 1
        # Take frame
        for _ in range(2):
            frame = camera.read_resize()
            if frame is None:
                print("Failed to capture frame")
                break

        _, output = finder.find_laser(frame, rectangles)
        if DEBUG and output is not None:
            cv2.imshow("Laser finder", output)

        if finder.laser_found():
            draw_visor_at_coord(frame, finder.get_laser_coord())

        if len(target) == 2:
            draw_target_at_coord(frame, target)

        if finder.laser_found() is not None and len(target) == 2:
            error = tracker.track_target_PID(finder.get_laser_coord(), target)
            # add error info to the frame
            cv2.putText(
                frame,
                text=f"Laser pos. error ={int(error)} px",
                org=(10, 100),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=0.5,
                color=(0, 255, 255),
            )
        else:
            tracker.reset_pos()

        add_exclusion_rectangles(frame, rectangles)
        add_camera_settings(camera.getVideoCapture(), frame)
        # add winning strategy info
        cv2.putText(
            frame,
            text=finder.get_winning_strategy(),
            org=(10, 120),
            fontFace=cv2.FONT_HERSHEY_COMPLEX,
            fontScale=0.5,
            color=(0, 255, 255),
        )
        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("p"):
            camera.set_exposure(camera.exposure + 1)
        if key == ord("m"):
            camera.set_exposure(camera.exposure - 1)

    cv2.destroyAllWindows()


point_and_shoot()
