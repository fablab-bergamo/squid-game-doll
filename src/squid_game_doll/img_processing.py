import cv2
from numpy.linalg import norm
import numpy as np
import pygame


def gamma(img: cv2.UMat, gamma: float) -> cv2.UMat:
    """
    Adjusts the gamma of the given image.

    Parameters:
    img (cv2.UMat): The input image.
    gamma (float): The gamma value to adjust.

    Returns:
    cv2.UMat: The gamma-adjusted image.
    """
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(img, table)


def brightness(img: cv2.UMat) -> cv2.UMat:
    """
    Calculates the brightness of the given image.

    Parameters:
    img (cv2.UMat): The input image.

    Returns:
    float: The brightness value of the image.
    """
    if len(img.shape) == 3:
        # Colored RGB or BGR (*Do Not* use HSV images with this function)
        # create brightness with euclidean norm
        return np.average(norm(img, axis=2)) / np.sqrt(3)
    else:
        # Grayscale
        return np.average(img)


def opencv_to_pygame(frame: np.ndarray, view_port: tuple[int, int]) -> pygame.Surface:
    """Converts an OpenCV frame to a PyGame surface.
    
    COORDINATE SYSTEM FOR GAMEPLAY:
    This function is used during gameplay to display the camera feed.
    The horizontal flip (cv2.flip with flag 1) creates a mirror effect that users expect.
    Game areas (start, finish, vision) are stored in original camera frame coordinates
    and are drawn BEFORE this flip is applied, so they appear in the correct positions
    after the flip.
    
    Parameters:
    frame (np.ndarray): The OpenCV frame to convert.
    view_port (tuple): The view port for the webcam (width, height).
    Returns:
    pygame.Surface: The PyGame surface.
    """
    pygame_frame: np.ndarray = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Flip along x-axis (1) - Creates mirror effect for natural user experience
    pygame_frame = cv2.flip(pygame_frame, 1)
    pygame_frame = cv2.resize(pygame_frame, view_port)
    # Rotate to match PyGame coordinates
    pygame_frame = cv2.rotate(pygame_frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return pygame.surfarray.make_surface(pygame_frame)
