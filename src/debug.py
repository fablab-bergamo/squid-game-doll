from squidgamesdoll.display import add_camera_settings, draw_visor_at_coord, draw_target_at_coord
from squidgamesdoll.tracker import track_target
from squidgamesdoll.laser_finder import LaserFinder
from squidgamesdoll.camera import Camera
from time import sleep

import cv2

target = ()


def click_event(event, x, y, flags, param):
    global target
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Click registered at ({x}, {y})")
        target = (x,y)

def point_and_shoot():
    WINDOW_NAME = "OpenCV"
    camera = Camera(0)
    camera.auto_exposure()
    
    cpt = 0
    
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)  # Create the window outside the loop
    cv2.setMouseCallback(WINDOW_NAME, click_event)  # Set mouse callback once

    finder = LaserFinder()

    while True:
        cpt += 1
        # Take each frame
        ret, frame = camera.read()
        if not ret:
            print("Failed to capture frame")
            break
        finder.find_laser(frame)
        
        if finder.laser_found():
            draw_visor_at_coord(frame, finder.get_laser_coord())
        
        if len(target) == 2:
            draw_target_at_coord(frame, target)

        if finder.laser_found() is not None and len(target) == 2:
            error = track_target(finder.get_laser_coord(), target)
            # add error info to the frame
            cv2.putText(frame,
                        text = f"Laser pos. error ={int(error)} px", 
                        org=(10, 100),
                        fontFace=cv2.FONT_HERSHEY_COMPLEX,
                        fontScale=0.5,
                        color=(0, 255, 255))

        add_camera_settings(camera.getVideoCapture(), frame)
        # add winning strategy info
        cv2.putText(frame,
                    text = finder.get_winning_strategy(), 
                    org=(10, 120),
                    fontFace=cv2.FONT_HERSHEY_COMPLEX,
                    fontScale=0.5,
                    color=(0, 255, 255))
        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord('p'):
            camera.set_exposure(camera.exposure + 1)
        if key == ord('m'):
            camera.set_exposure(camera.exposure - 1)
    
    cv2.destroyAllWindows()

point_and_shoot()