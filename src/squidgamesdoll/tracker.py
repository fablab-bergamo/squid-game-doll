import cv2
from numpy.linalg import norm
import numpy as np
import socket
from time import sleep, time
from simple_pid import PID

pid_v = PID(1, 0.1, 0.05, setpoint=0, output_limits=(100,180), starting_output=135)
pid_h = PID(1, 0.1, 0.05, setpoint=0, output_limits=(90,170), starting_output=135)
pid_h.sample_time = 0.5
pid_v.sample_time = 0.5 

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

    step_v = min(max(0.4, abs(vertical_error / 100.0)), 10)
    step_h = min(max(0.5, abs(horizontal_error / 100.0)), 10)

    print(f"Step V {step_v}, step H {step_h}")
    send_instructions(up, down, left, right, step_v, step_h)
    # Send the updated angles to ESP32
    return error

prev_output_h = 100
prev_output_v = 100

def track_target_PID(laser:tuple, target:tuple) -> float:
    """
    Tracks the target position relative to the laser position and provides feedback.

    Parameters:
    laser (tuple): The (x, y) coordinates of the laser position.
    target (tuple): The (x, y) coordinates of the target position.

    Returns:
    float: The positioning error in absolute distance.
    """
    global prev_output_v, prev_output_h
    RATE_OF_CHANGE = 1

    # compute the positionning error in abs distance
    if target is None or laser is None:
        return 0
    
    error = norm(np.array(laser) - np.array(target))

    vertical_error = -(laser[0] - target[0])
    horizontal_error = -(laser[1] - target[1])

    output_h = pid_h(horizontal_error)
    output_v = pid_v(vertical_error)

    if abs(output_h - prev_output_h) > RATE_OF_CHANGE:
        if (output_h > prev_output_h):
            output_h = prev_output_h + RATE_OF_CHANGE
        else:
            output_h = prev_output_h - RATE_OF_CHANGE
    
    if abs(output_v - prev_output_v) > RATE_OF_CHANGE:
        if (output_v > prev_output_v):
            output_v = prev_output_v + RATE_OF_CHANGE
        else:
            output_v = prev_output_v - RATE_OF_CHANGE
    

    prev_output_h = output_h
    prev_output_v = output_v
    print(f"output_h {output_h}, output_v {output_v}")

    send_angles((output_h, output_v))

    return error

DEFAULT_POS = (135.0,137.5)
current_pos = (135.0,137.5)
aliensocket = None
last_sent = 0

def reset_pos():
    global current_pos, DEFAULT_POS
    send_angles(DEFAULT_POS)
    current_pos = DEFAULT_POS


def send_angles(angles:tuple) -> bool:
    global current_pos, aliensocket

    if aliensocket is None:
        aliensocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            aliensocket.connect(('192.168.2.55', 15555))
        except:
            return False

    data = bytes(str((angles[1], angles[0])), "utf-8")
    try:
        aliensocket.send(data)
    except:
        aliensocket = None
        return False

    return True

def send_instructions(up:bool,down:bool,left:bool,right:bool,step_v:float, step_h:float) -> bool:
    global current_pos, aliensocket
    global last_sent

    if time() - last_sent > 0.2:
        last_sent = time()
    else:
        return True

    if up:
        current_pos = (current_pos[0], current_pos[1] - step_v)
    if down:
        current_pos = (current_pos[0], current_pos[1] + step_v)
    if left:
        current_pos = (current_pos[0] - step_h, current_pos[1])
    if right:
        current_pos = (current_pos[0] + step_h, current_pos[1])
    
    # Limits
    if current_pos[0] < 0:
        current_pos = (0, current_pos[1])
    if current_pos[0] > 180:
        current_pos = (180, current_pos[1])
    
    if current_pos[1] < 0:
        current_pos = (current_pos[0] , 0)
    if current_pos[1] > 180:
        current_pos = (current_pos[0] , 180)

    return send_angles(current_pos)