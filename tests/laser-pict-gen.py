import cv2
import random

FILE_NAME = "pictures\\frame-10.jpg"

def add_laser_dot(img: cv2.UMat, pos: tuple):
    output = img.copy()
    k = 0.75 + random.random() * 0.25
    main = random.randint(3,7)
    for radius in range(main, 0, -1):
        if radius == 1:
            color = (255,255,255)
        else:
            color = (0, 0, 255 - radius * 10 + random.randint(0,5))

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

def generate_test_images(num: int) -> (list, list):
    images = []
    coords = []
    
    for _ in range(num):    
        img = cv2.imread(f"pictures\\frame-{random.randint(1,26)*10}.jpg")
        height, width = img.shape[:2]
        # choose random position for laser dot
        (x,y) = (random.randint(0, height), random.randint(0, width))
        images.append(add_laser_dot(img, (x,y)))
        coords.append((x,y))
    return (images, coords)

def find_laser(img: cv2.UMat) -> (tuple, cv2.UMat):
    strategies = [find_laser_by_grayscale, find_laser_by_color]
    for strategy in strategies:
        (coord, output) = strategy(img)
        if coord is not None:
            return (coord, output)
    return (None, None)

def find_laser_by_threshold(channel: cv2.UMat) -> (tuple, cv2.UMat):
    done = False
    threshold = 180
    while not done:
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
            threshold -= (threshold - 100) // 2
            print(f"Found no circles, decreasing threshold to {threshold}")
            if threshold < 100:
                return (None, None)
            continue
            
        if circles_cpt > 1:
            threshold += (255 - threshold) // 2
            print(f"Found {circles_cpt} circles, increasing threshold to {threshold}")
            if threshold > 255:
                return (None, None)
            continue
        
        print(f"Found 1 circle, threshold={threshold}")
        done = True
        # draw circles found
        output = cv2.cvtColor(masked_channel, cv2.COLOR_GRAY2BGR)
        #output = cv2.addWeighted(img, 0.2, output, 0.1, 0)
    
        for circle in circles[0,:]:
            center = (int(circle[0]), int(circle[1]))
            cv2.circle(img=output, center=center, radius=5, color=(255,0,0), thickness=3)
            return (center, output)
        
    return (None, None)

def find_laser_by_grayscale(img: cv2.UMat) -> (tuple, cv2.UMat):
    gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    normalized_gray_image = cv2.normalize(gray_image, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    return find_laser_by_threshold(normalized_gray_image)

def find_laser_by_color(img: cv2.UMat) -> (tuple, cv2.UMat):
    (B, G, R) = cv2.split(img)
    return find_laser_by_threshold(R)
   



num = int(input("Enter the number of images to generate: "))
outputs = []
(images, coords) = generate_test_images(num)
for img in images:
    (pos, output) = find_laser(img)
    if pos is not None:
        outputs.append(output)

cv2.imshow("Inputs", compose_images(images))
cv2.imshow("Results", compose_images(outputs))
cv2.waitKey(0)
cv2.destroyAllWindows()