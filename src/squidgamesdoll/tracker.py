import cv2
from numpy.linalg import norm
import numpy as np

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
    error = norm(np.array(laser) - np.array(target))

    vertical_error = laser[0] - target[0]
    horizontal_error = laser[1] - target[1]
    
    if vertical_error < -10:
        print("Move up")
    elif vertical_error > 10:
        print("Move down")

    if horizontal_error < -10:
        print("Move left")
    elif horizontal_error > 10:
        print("Move right")

    # Send the updated angles to ESP32
    return error
