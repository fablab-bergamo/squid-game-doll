from __future__ import print_function
import cv2 as cv
import argparse
import numpy as np
import socket
import random
from time import sleep

parser = argparse.ArgumentParser(description='This program shows how to use background subtraction methods provided by \
                                              OpenCV. You can process both videos and images.')
parser.add_argument('--input', type=str, help='Path to a video or a sequence of image.', default='D:\\GitHub\\squid-game-doll\\pictures\\laser.mp4')
parser.add_argument('--algo', type=str, help='Background subtraction method (KNN, MOG2).', default='MOG2')
args = parser.parse_args()
if args.algo == 'MOG2':
    backSub = cv.createBackgroundSubtractorMOG2()
else:
    backSub = cv.createBackgroundSubtractorKNN()

capture = cv.VideoCapture(0) #cv.samples.findFileOrKeep(args.input))
capture.set(cv.CAP_PROP_BUFFERSIZE, 1)
capture.set(cv.CAP_PROP_FPS, 10.0)
print(f"Exposure={capture.get(cv.CAP_PROP_EXPOSURE)}")
capture.set(cv.CAP_PROP_FRAME_WIDTH, 1024)
capture.set(cv.CAP_PROP_FRAME_HEIGHT, 768)
capture.set(cv.CAP_PROP_EXPOSURE, -8)

#capture = cv.VideoCapture(cv.samples.findFileOrKeep(args.input))
esp32sock = None

if not capture.isOpened():
    print('Unable to open: ' + args.input)
    exit(0)

def try_send(msg: str):
    global esp32sock

    try:
        if esp32sock is None:
            esp32sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            esp32sock.connect(('192.168.1.220', 15555))
        data = bytes(msg, "utf-8")
        esp32sock.send(data)
    except:
        print("Error sending message to ESP32")
        esp32sock = None
        

def collect_median_frame(capture:cv.VideoCapture, socket:socket.socket) -> np.ndarray:
    print("Collecting reference frame")
    try_send("off")
    sleep(0.1)
    _, frame = capture.read()
    _, frame = capture.read()
    _, frame = capture.read()
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    try_send("on")
    return gray

frameCpt = 0
medianFrame = collect_median_frame(capture, esp32sock)
while True:
    ret, frame = capture.read()
    if frame is None:
        break
    
    frameCpt += 1

    # Calculate the median along the time axis
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    # Store selected frames in an array
    if (frameCpt % 10 == 0):
        medianFrame = collect_median_frame(capture, esp32sock)

    dframe = cv.absdiff(gray, medianFrame)
    th, dframe = cv.threshold(dframe, 50, 255, cv.THRESH_TOZERO)
    
    # Show keypoints
    cv.imshow("output", frame)
    cv.imshow('dframe', dframe)
    cv.imshow('medianFrame', medianFrame)

    keyboard = cv.waitKey(15)
    if keyboard == 'q' or keyboard == 27:
        break

esp32sock.close()