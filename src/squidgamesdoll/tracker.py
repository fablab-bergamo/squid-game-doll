import cv2
from numpy.linalg import norm
import numpy as np
import socket
from time import sleep, time
from simple_pid import PID

pid_v = PID(0.1, 0.01, 0.005, setpoint=0, output_limits=(105,170), starting_output=135)
pid_h = PID(0.1, 0.01, 0.005, setpoint=0, output_limits=(90,180), starting_output=135)
pid_h.sample_time = 0.3
pid_v.sample_time = 0.3

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

    step_v = min(max(1, abs(vertical_error / 100.0)), 10)
    step_h = min(max(1, abs(horizontal_error / 100.0)), 10)
    send_instructions(up, down, left, right, step_v, step_h)
    # Send the updated angles to ESP32
    return error

def track_target_PID(laser:tuple, target:tuple) -> float:
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

    output_h = pid_h(horizontal_error)
    output_v = pid_v(vertical_error)

    send_angles((output_h, output_v))

    return error


current_pos = (135.0,137.5)
aliensocket = None
last_sent = 0


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