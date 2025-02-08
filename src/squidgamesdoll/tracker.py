import cv2
from numpy.linalg import norm
import numpy as np
import socket
from time import sleep, time

def track_target(laser:tuple, target:tuple) -> float:
    """
    Tracks the target position relative to the laser position and provides feedback.

    Parameters:
    laser (tuple): The (x, y) coordinates of the laser position.
    target (tuple): The (x, y) coordinates of the target position.

    Returns:
    float: The positioning error in absolute distance.
    """
    # compute the positionning error in abs distance
    if target is None or laser is None:
        return 0
    
    error = norm(np.array(laser) - np.array(target))

    vertical_error = laser[0] - target[0]
    horizontal_error = laser[1] - target[1]
    up = False
    down = False
    left = False
    right = False

    if vertical_error < -10:
        up = True
    elif vertical_error > 10:
        down = True

    if horizontal_error < -10:
        left = True
    elif horizontal_error > 10:
        right = True

    send_instructions(up, down, left, right)
    # Send the updated angles to ESP32
    return error

current_pos = (135.0,137.5)
aliensocket = None
last_sent = 0

def send_instructions(up:bool,down:bool,left:bool,right:bool):
    global current_pos, aliensocket
    global last_sent

    if time() - last_sent > 0.3:
        last_sent = time()
    else:
        return
    
    if aliensocket is None:
        aliensocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        aliensocket.connect(('192.168.45.66', 15555))

    if up:
        current_pos = (current_pos[0], current_pos[1] - 1)
    if down:
        current_pos = (current_pos[0], current_pos[1] + 1)
    if left:
        current_pos = (current_pos[0] - 1, current_pos[1])
    if right:
        current_pos = (current_pos[0] + 1, current_pos[1])
    
    if current_pos[0] < 0:
        current_pos = (0, current_pos[1])
    if current_pos[0] > 180:
        current_pos = (180, current_pos[1])
    
    if current_pos[1] < 0:
        current_pos = (current_pos[0] , 0)
    if current_pos[1] > 180:
        current_pos = (current_pos[0] , 180)

    data = bytes(str((current_pos[1], current_pos[0])), "utf-8")
    try:
        aliensocket.send(data)
    except:
        aliensocket = None

    sleep(0.1)