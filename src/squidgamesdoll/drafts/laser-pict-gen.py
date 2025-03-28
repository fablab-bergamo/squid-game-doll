import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

from time import sleep
import cv2
import random
import numpy as np
from numpy.linalg import norm

FILE_NAME = "pictures\\frame-10.jpg"
last_render = 0
#This variable we use to store the pixel location
target = ()

def add_laser_dot(img: cv2.UMat, pos: tuple):
    output = img.copy()
    k = 0.75 + random.random() * 0.25
    main = random.randint(3,7)
    max_laser = random.randint(240, 255)
    for radius in range(main, 0, -1):
        if radius <= 2:
            color = (max_laser,max_laser,max_laser)
        else:
            color = (0, 0, max_laser - radius * 10 + random.randint(0,5))

        output = cv2.ellipse(img=output, center=pos, 
                            axes=(radius, int(radius * k)),
                            angle=180.0,
                            startAngle=0, endAngle=360,
                            color=color, thickness=2)
    return output

def compose_images(images: list) -> cv2.UMat:
    images_per_row = 3
    num_images = len(images)
    rows = num_images // images_per_row 
    if num_images % images_per_row != 0:
        rows += 1
    height, width = images[0].shape[:2]
    # create a blank image to store the composed images
    output = cv2.resize(images[0], (width * images_per_row, height * rows))
    output.fill(0)

    for i in range(0, num_images):
        row = i // images_per_row
        col = i % images_per_row
        output[height*row:height*(row+1), width*col:width*(col+1)] = images[i]
    # resize by 50% for better viewing
    output = cv2.resize(output, (width * images_per_row // 2, height * rows // 2))
    return output

def gamma(img: cv2.UMat, gamma: float) -> cv2.UMat:
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
        for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(img, table)

def generate_test_images(num: int) -> dict:
    images = []
    coords = []
    
    for _ in range(num):    
        img = cv2.imread(f"pictures\\frame-{random.randint(1,26)*10}.jpg")
        # choose random position for laser dot
        height, width = img.shape[:2]
        coord = (random.randint(0, height-5)+5, random.randint(0, width-5)+5)

        img = add_laser_dot(img, coord)
        
        img = gamma(img, random.random() * 0.8 + 0.5)
        
        images.append(img)
        coords.append(coord)
    
    return {"images": images, 
            "coords": coords}

def brightness(img):
    if len(img.shape) == 3:
        # Colored RGB or BGR (*Do Not* use HSV images with this function)
        # create brightness with euclidean norm
        return np.average(norm(img, axis=2)) / np.sqrt(3)
    else:
        # Grayscale
        return np.average(img)

def draw_visor_at_coord(img: cv2.UMat, coord: tuple) -> cv2.UMat:
    cv2.line(img, (coord[0] - 10, coord[1]), (coord[0] - 5, coord[1]), (0, 255, 0), 2)
    cv2.line(img, (coord[0] + 5, coord[1]), (coord[0] + 10, coord[1]), (0, 255, 0), 2)
    cv2.line(img, (coord[0], coord[1] - 10), (coord[0], coord[1] - 5), (0, 255, 0), 2)
    cv2.line(img, (coord[0], coord[1] + 5), (coord[0], coord[1] + 10), (0, 255, 0), 2)
    cv2.rectangle(img, (coord[0] -14, coord[1] - 14), (coord[0] + 14, coord[1] + 14), (0, 255, 0), 2)
    return img

def draw_target_at_coord(img: cv2.UMat, coord: list) -> cv2.UMat:
    if coord is None or len(coord) != 2:
        return img
    cv2.line(img, (coord[0] - 5, coord[1]), (coord[0] - 1, coord[1]), (0, 0, 255), 1)
    cv2.line(img, (coord[0] + 1, coord[1]), (coord[0] + 5, coord[1]), (0, 0, 255), 1)
    cv2.line(img, (coord[0], coord[1] - 5), (coord[0], coord[1] - 1), (0, 0, 255), 1)
    cv2.line(img, (coord[0], coord[1] + 1), (coord[0], coord[1] + 5), (0, 0, 255), 1)
    return img
  
def find_laser(img: cv2.UMat, strategy_hint: str, threshold_hint: int) -> (tuple, cv2.UMat, str, int):
    strategies = [find_laser_by_red_color, find_laser_by_grayscale, find_laser_by_green_color]
    
    if strategy_hint is not None:
        # sort strategies by hint
        strategies.sort(key=lambda x: x.__name__ == strategy_hint, reverse=True)

    for strategy in strategies:
        print(f"Trying strategy {strategy.__name__}")   
        (coord, output, threshold) = strategy(img.copy(), threshold_hint)
        if coord is not None:
            print(f"Found laser at {coord}")
            cv2.putText(output, 
                text = strategy.__name__, 
                org=(10, 40),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=.5,
                color=(0, 255, 0))
            cv2.putText(output, 
                text = f"Brightness={int(brightness(img))}", 
                org=(10, 60),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=.5,
                color=(0, 255, 0))
            return (coord, output, strategy.__name__, threshold)
    return (None, None, None, None)

def find_laser_by_threshold(channel: cv2.UMat, threshold_hint:int) -> (tuple, cv2.UMat, int):
    MAX_TRIES = 7
    MIN_THRESHOLD = 100
    MAX_THRESHOLD = 255
    threshold = (MIN_THRESHOLD + MAX_THRESHOLD) // 2
    
    if (threshold_hint is not None and threshold_hint > MIN_THRESHOLD and threshold_hint < MAX_THRESHOLD):
        threshold = threshold_hint

    tries = 0
    while tries < MAX_TRIES:
        _, diff_thr = cv2.threshold(channel, threshold, 255, cv2.THRESH_TOZERO)
        #cv2.imshow("Threshold", cv2.cvtColor(diff_thr, cv2.COLOR_GRAY2BGR))
        
        masked_channel = cv2.dilate(diff_thr, None, iterations=4)
        #cv2.imshow("Dilate", cv2.cvtColor(masked_channel, cv2.COLOR_GRAY2BGR))

        circles = cv2.HoughCircles(masked_channel, cv2.HOUGH_GRADIENT, 1, minDist=50,
                                param1=50,param2=2,minRadius=3,maxRadius=10)
        
        if circles is None:
            circles_cpt = 0
        else:
            circles_cpt = len(circles[0,:])
        
        if circles_cpt == 0:
            step = (threshold - MIN_THRESHOLD) // 2
            if step == 0:
                step = 1
            threshold -= step 
            print(f"Found no circles, decreasing threshold to {threshold}")
            if threshold < MIN_THRESHOLD:
                return (None, None, None)
            tries += 1
            continue
            
        if circles_cpt > 1:
            step = (MAX_THRESHOLD - threshold) // 2
            if step == 0:
                step = 1
            threshold += step
            print(f"Found {circles_cpt} circles, increasing threshold to {threshold}")
            if threshold > MAX_THRESHOLD:
                return (None, None, None)
            tries += 1
            continue
        
        print(f"Found 1 circle, threshold={threshold}")

        # draw circles found
        output = cv2.cvtColor(masked_channel, cv2.COLOR_GRAY2BGR)
        background = cv2.cvtColor(channel, cv2.COLOR_GRAY2BGR)

        for circle in circles[0,:]:
            center = (int(circle[0]), int(circle[1]))
            output = cv2.addWeighted(background, 0.2, output, 0.5, 0)
            cv2.putText(output, 
                        text = "THR="+ str(threshold), 
                        org=(10, 20),
                        fontFace=cv2.FONT_HERSHEY_COMPLEX,
                        fontScale=0.5,
                        color=(0, 255, 0))
            return (center, output, threshold)
        
    return (None, None, None)

def find_laser_by_grayscale(img: cv2.UMat, hint:int) -> (tuple, cv2.UMat, int):
    gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    normalized_gray_image = cv2.normalize(gray_image, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    return find_laser_by_threshold(normalized_gray_image, hint)

def find_laser_by_red_color(img: cv2.UMat, hint:int) -> (tuple, cv2.UMat, int):
    (_, _, R) = cv2.split(img)
    return find_laser_by_threshold(R, hint)
   
def find_laser_by_green_color(img: cv2.UMat, hint:int) -> (tuple, cv2.UMat, int):
    (_, G, _) = cv2.split(img)
    return find_laser_by_threshold(G, hint)


def set_exposure(cap: cv2.VideoCapture, exposure: int):
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3) # auto mode
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1) # manual mode
    cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
    sleep(1)

def setup_webcam(index: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)
    cap.set(cv2.CAP_PROP_FPS, 10.0)
    return cap

def add_camera_settings(cap: cv2.VideoCapture, frame: cv2.UMat) -> cv2.UMat:
    global last_render
    if last_render == 0:
        last_render = cv2.getTickCount()
    
    # compute fps
    current_time = cv2.getTickCount()
    time_diff = (current_time - last_render) / cv2.getTickFrequency()
    last_render = current_time
    fps = int(1.0 / time_diff)

    cv2.putText(frame,
                text = f"Act. FPS={fps}", 
                org=(10, 80),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=0.5,
                color=(255, 255, 255))

    cv2.putText(frame,
                text = f"Picture={int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}", 
                org=(10, 20),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=0.5,
                color=(255, 255, 255))
    cv2.putText(frame,
                text = f"Webcam FPS={cap.get(cv2.CAP_PROP_FPS)}", 
                org=(10, 40),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=0.5,
                color=(255, 255, 255))
    cv2.putText(frame,
                text = f"Exposure={cap.get(cv2.CAP_PROP_EXPOSURE)}", 
                org=(10, 60),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=0.5,
                color=(255, 255, 255))
    return frame

def click_event(event, x, y, flags, param):
    global target
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Click registered at ({x}, {y})")
        target = (x,y)

def webcam_test():
    WINDOW_NAME = "OpenCV"
    cap = setup_webcam(0)
    exposure = -7
    set_exposure(cap, exposure)
    cpt = 0
    thr_hint = None
    str_hint = None
    while True:
        cpt += 1
        # Take each frame
        ret, frame = cap.read()
        (coord, picture, str_hint, thr_hint) = find_laser(frame, str_hint, thr_hint)
        if coord is None:
            picture = np.zeros(frame.shape, dtype="uint8")
        else:
            draw_visor_at_coord(frame, coord)
        add_camera_settings(cap, frame)
        result = cv2.hconcat([frame, picture])
        cv2.imshow(WINDOW_NAME, result)
        key = cv2.waitKey(2) & 0xFF
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

def track_target(laser:tuple, target:tuple, frame:cv2.UMat):
    # compute the positionning error in abs distance
    error = norm(np.array(laser) - np.array(target))

    # add error info to the frame
    cv2.putText(frame,
                text = f"Laser pos. error ={int(error)} px", 
                org=(10, 100),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=0.5,
                color=(0, 255, 255))
    
    vertical_error = laser[0] - target[0]
    horizontal_error = laser[1] - target[1]

    if error < 10:
        # good enough
        return
    
    if vertical_error < -10:
        print("Move up")
    elif vertical_error > 10:
        print("Move down")

    if horizontal_error < -10:
        print("Move left")
    elif horizontal_error > 10:
        print("Move right")

    # Send the updated angles to ESP32
    return


def point_and_shoot():
    WINDOW_NAME = "OpenCV"
    cap = setup_webcam(0)
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
        (coord, _, str_hint, thr_hint) = find_laser(frame, str_hint, thr_hint)
        
        if coord is not None:
            draw_visor_at_coord(frame, coord)
        
        if len(target) == 2:
            draw_target_at_coord(frame, target)

        if coord is not None and len(target) == 2:
            track_target(coord, target, frame)

        add_camera_settings(cap, frame)
        cv2.imshow(WINDOW_NAME, frame)
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

def file_test():
    num = int(input("Enter the number of images to generate: "))
    outputs = []
    items = generate_test_images(num)
    for i in range(len(items["images"])):
        img = items["images"][i]
        true_pos = items["coords"][i]
        (pos, output) = find_laser(img)
        if pos is not None:
            print(f"True position={true_pos}, found position={pos}")
            error = int(norm(np.array(true_pos) - np.array(pos)))
            if error > 10:
                color = (0, 0, 255)
            else:
                color = (0, 255, 0)
                
            cv2.putText(output,
                text = f"Error={error}", 
                        org=(10, 160),
                        fontFace=cv2.FONT_HERSHEY_COMPLEX,
                        fontScale=1,
                        color=color)
            outputs.append(output)

    cv2.imshow("Inputs", compose_images(items["images"]))
    cv2.imshow("Results", compose_images(outputs))
    cv2.waitKey(0)
    cv2.destroyAllWindows()


#file_test()
#webcam_test()
point_and_shoot()