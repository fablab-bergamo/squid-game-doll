import squidgamesdoll
from squidgamesdoll.camera import setup_webcam, set_exposure
from squidgamesdoll.display import add_camera_settings, draw_visor_at_coord, draw_target_at_coord
from squidgamesdoll.tracker import track_target
from squidgamesdoll.laser import find_laser
from time import sleep
import numpy as np

import cv2

target = ()


def click_event(event, x, y, flags, param):
    global target
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Click registered at ({x}, {y})")
        target = (x,y)

def point_and_shoot():
    WINDOW_NAME = "OpenCV"
    cap = setup_webcam(2)
    exposure = -7
    set_exposure(cap, exposure)
    cpt = 0
    thr_hint = None
    str_hint = None
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)  # Create the window outside the loop
    cv2.setMouseCallback(WINDOW_NAME, click_event)  # Set mouse callback once

    while True:
        cpt += 1
        # Take each frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break
        if frame.shape[1] != 960 or frame.shape[0] != 720:
            cv2.resize(frame, (960, 720))
            
        (coord, output, str_hint, thr_hint) = find_laser(frame, str_hint, thr_hint)
        
        if coord is not None:
            draw_visor_at_coord(frame, coord)
        if output is None:
            output = np.zeros(frame.shape, dtype="uint8")

        if len(target) == 2:
            draw_target_at_coord(frame, target)

        if coord is not None and len(target) == 2:
            error = track_target(coord, target)
            # add error info to the frame
            cv2.putText(frame,
                        text = f"Laser pos. error ={int(error)} px", 
                        org=(10, 100),
                        fontFace=cv2.FONT_HERSHEY_COMPLEX,
                        fontScale=0.5,
                        color=(0, 255, 255))

        add_camera_settings(cap, frame)

        cv2.imshow(WINDOW_NAME, cv2.vconcat([frame, output]))
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord('p'):
            exposure += 1
            set_exposure(cap, exposure)
            sleep(1)
        if key == ord('m'):
            exposure -= 1
            set_exposure(cap, exposure)
            sleep(1)
    cap.release()
    cv2.destroyAllWindows()

point_and_shoot()