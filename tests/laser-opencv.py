# individua un punto laser rosso

import cv2
import numpy as np
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1680)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 5.0)
cap.set(cv2.CAP_PROP_EXPOSURE, -7)

pts = []
cpt = 0
last_pos = (512,369)

while (1):
    cpt += 1
    # Take each frame
    ret, frame = cap.read()
    
    (B, G, R) = cv2.split(frame)
    zeros = np.zeros(frame.shape[:2], dtype="uint8")
    cv2.imshow("Red", cv2.merge([zeros, zeros, R]))
    cv2.imshow("Green", cv2.merge([zeros, G, zeros]))
    cv2.imshow("Blue", cv2.merge([B, zeros, zeros]))
    channel = G.copy()

    #cv2.GaussianBlur(g, (5,5), 0, g)

    r,diff_thr = cv2.threshold(channel, 200, 255, cv2.THRESH_TOZERO)
    
    masked_channel = cv2.bitwise_and(channel, channel, None, diff_thr)
    
    cv2.imshow('masked_channel', masked_channel)

    output = frame.copy()

    circles = cv2.HoughCircles(masked_channel, cv2.HOUGH_GRADIENT, 1, minDist=50,
                             param1=50,param2=2,minRadius=3,maxRadius=10)

    if circles is not None and len(circles) > 0 and len(circles[0]) > 0:
        circle = circles[0]

        #find the position closest to the last position
        min_dist = 100000
        best_pos = last_pos
        for circle in circles[0,:]:
            dist = np.linalg.norm(np.array([circle[0],circle[1]]) - np.array(last_pos))
            if dist < min_dist:
                min_dist = dist
                best_pos = np.array([circle[0]+circle[2]/2,circle[1]+circle[2]/2])
        last_pos = (int(best_pos[0]), int(best_pos[1]))
        found = True
    else:
        found = False

    if found:
        cv2.circle(img=output, center=last_pos, radius=1, color=(0,255,0), thickness=2)
        print(f"Laser position={last_pos}")
        
    
    cv2.imshow('Output', output)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()