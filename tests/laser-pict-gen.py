import cv2
import random
import numpy as np
from numpy.linalg import norm

FILE_NAME = "pictures\\frame-10.jpg"

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
    
def find_laser(img: cv2.UMat) -> (tuple, cv2.UMat):
    strategies = [find_laser_by_red_color, find_laser_by_grayscale, find_laser_by_green_color]
    for strategy in strategies:
        print(f"Trying strategy {strategy.__name__}")   
        (coord, output) = strategy(img.copy())
        if coord is not None:
            cv2.putText(output, 
                text = strategy.__name__, 
                org=(10, 70),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=1,
                color=(255, 255, 255))
            cv2.putText(output, 
                text = f"Brightness={int(brightness(img))}", 
                org=(10, 110),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=1,
                color=(255, 255, 255))
            return (coord, output)
    return (None, None)

def find_laser_by_threshold(channel: cv2.UMat) -> (tuple, cv2.UMat):
    MAX_TRIES = 7
    MIN_THRESHOLD = 100
    MAX_THRESHOLD = 255
    threshold = (MIN_THRESHOLD + MAX_THRESHOLD) // 2
    tries = 0
    while tries < MAX_TRIES:
        _, diff_thr = cv2.threshold(channel, threshold, 255, cv2.THRESH_TOZERO)
        masked_channel = cv2.bitwise_and(channel, channel, None, diff_thr)
        masked_channel = cv2.dilate(masked_channel, None, iterations=4)
        circles = cv2.HoughCircles(masked_channel, cv2.HOUGH_GRADIENT, 1, minDist=50,
                                param1=50,param2=2,minRadius=3,maxRadius=10)
        
        if circles is None:
            circles_cpt = 0
        else:
            circles_cpt = len(circles[0,:])
        
        if circles_cpt == 0:
            step = (threshold - 100) // 2
            if step == 0:
                step = 1
            threshold -= step 
            print(f"Found no circles, decreasing threshold to {threshold}")
            if threshold < MIN_THRESHOLD:
                return (None, None)
            tries += 1
            continue
            
        if circles_cpt > 1:
            step = (255 - threshold) // 2
            if step == 0:
                step = 1
            threshold += step
            print(f"Found {circles_cpt} circles, increasing threshold to {threshold}")
            if threshold > MAX_THRESHOLD:
                return (None, None)
            tries += 1
            continue
        
        print(f"Found 1 circle, threshold={threshold}")
        done = True
        # draw circles found
        output = cv2.cvtColor(masked_channel, cv2.COLOR_GRAY2BGR)
    
        for circle in circles[0,:]:
            center = (int(circle[0]), int(circle[1]))
            output = cv2.addWeighted(img, 0.2, output, 0.5, 0)
            cv2.circle(img=output, center=center, radius=5, color=(255,255,255), thickness=2)
            cv2.putText(output, 
                        text = "THR="+ str(threshold), 
                        org=(10, 30),
                        fontFace=cv2.FONT_HERSHEY_COMPLEX,
                        fontScale=1,
                        color=(255, 255, 255))
            return (center, output)
        
    return (None, None)

def find_laser_by_grayscale(img: cv2.UMat) -> (tuple, cv2.UMat):
    gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    normalized_gray_image = cv2.normalize(gray_image, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    return find_laser_by_threshold(normalized_gray_image)

def find_laser_by_red_color(img: cv2.UMat) -> (tuple, cv2.UMat):
    (_, _, R) = cv2.split(img)
    return find_laser_by_threshold(R)
   
def find_laser_by_green_color(img: cv2.UMat) -> (tuple, cv2.UMat):
    (_, G, _) = cv2.split(img)
    return find_laser_by_threshold(G)



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