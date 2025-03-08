# riconosce linee e le loro intersezioni

import cv2
from time import sleep
import numpy as np
import math
from collections import defaultdict

def segment_by_angle_kmeans(lines, k=2, **kwargs):
    """
    Group lines by their angle using k-means clustering.

    Code from here:
    https://stackoverflow.com/a/46572063/1755401
    """

    # Define criteria = (type, max_iter, epsilon)
    default_criteria_type = cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER
    criteria = kwargs.get('criteria', (default_criteria_type, 10, 1.0))

    flags = kwargs.get('flags', cv2.KMEANS_RANDOM_CENTERS)
    attempts = kwargs.get('attempts', 10)

    # Get angles in [0, pi] radians
    angles = np.array([line[0][1] for line in lines])

    # Multiply the angles by two and find coordinates of that angle on the Unit Circle
    pts = np.array([[np.cos(2*angle), np.sin(2*angle)] for angle in angles], dtype=np.float32)

    # Run k-means
    labels, centers = cv2.kmeans(pts, k, None, criteria, attempts, flags)[1:]

    labels = labels.reshape(-1) # Transpose to row vector

    # Segment lines based on their label of 0 or 1
    segmented = defaultdict(list)
    for i, line in zip(range(len(lines)), lines):
        segmented[labels[i]].append(line)

    segmented = list(segmented.values())
    if len(segmented) > 1:
        print("Segmented lines into two groups: %d, %d" % (len(segmented[0]), len(segmented[1])))

    return segmented

def intersection(line1, line2):
    """
    Find the intersection of two lines 
    specified in Hesse normal form.

    Returns closest integer pixel locations.

    See here:
    https://stackoverflow.com/a/383527/5087436
    """

    rho1, theta1 = line1[0]
    rho2, theta2 = line2[0]
    A = np.array([[np.cos(theta1), np.sin(theta1)],
                  [np.cos(theta2), np.sin(theta2)]])
    b = np.array([[rho1], [rho2]])
    x0, y0 = np.linalg.solve(A, b)
    x0, y0 = int(np.round(x0)), int(np.round(y0))

    return [[x0, y0]]

def segmented_intersections(lines):
    """
    Find the intersection between groups of lines.
    """

    intersections = []
    for i, group in enumerate(lines[:-1]):
        for next_group in lines[i+1:]:
            for line1 in group:
                for line2 in next_group:
                    intersections.append(intersection(line1, line2)) 

    return intersections

# Open the default camera
cam = cv2.VideoCapture(1)

# Get the default frame width and height
frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Define the codec and create VideoWriter object
#fourcc = cv2.VideoWriter_fourcc(*"mp4v")
#out = cv2.VideoWriter("output.mp4", fourcc, 20.0, (frame_width, frame_height))

threshold_min = 50
threshold_max = 250

while True:
    ret, frame = cam.read()

    # Write the frame to the output file
    #out.write(frame)
    b,g,r = cv2.split(frame)

    dst = cv2.Canny(r, threshold_min, threshold_max, apertureSize=3)
    lines = cv2.HoughLinesP(dst,rho = 1,theta = 1*np.pi/180,threshold = 100,minLineLength = 100,maxLineGap = 50)

    if lines is not None:
        if len(lines) > 100:
            print("Found too many lines")
            continue
        segmented = segment_by_angle_kmeans(lines, 2)
        if len(segmented) < 2:
            intersections = []
        else:
            intersections = segmented_intersections(segmented)
        for line in lines:
            rho = line[0][0]
            theta = line[0][1]
            a = math.cos(theta)
            b = math.sin(theta)
            x0 = a * rho
            y0 = b * rho
            pt1 = (int(x0 + 1000*(-b)), int(y0 + 1000*(a)))
            pt2 = (int(x0 - 1000*(-b)), int(y0 - 1000*(a)))
            cv2.line(frame, pt1, pt2, (0,0,255), 3, cv2.LINE_AA)
        # Draw intersection points in magenta
        for point in intersections:
            pt = (point[0][0], point[0][1])
            length = 5
            cv2.line(frame, (pt[0], pt[1]-length), (pt[0], pt[1]+length), (255, 0, 255), 1) # vertical line
            cv2.line(frame, (pt[0]-length, pt[1]), (pt[0]+length, pt[1]), (255, 0, 255), 1)

    
    # Display the captured frame
    cv2.imshow("laser red", dst);
    cv2.imshow("corner", frame)
    # Press 'q' to exit the loop
    if cv2.waitKey(1) == ord("q"):
        break
    if cv2.waitKeyEx(1) == 2424832:
        threshold_min -= 10
    if cv2.waitKeyEx(1) == 2555904:
        threshold_min += 10
    if cv2.waitKeyEx(1) == 2621440:
        threshold_max -= 10
    if cv2.waitKeyEx(1) == 2490368:
        threshold_max += 10
    sleep(0.01)

# Release the capture and writer objects
cam.release()
#out.release()
cv2.destroyAllWindows()
