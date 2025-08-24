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
    """Converts an OpenCV frame to a PyGame surface using optimized numpy operations.
    
    COORDINATE SYSTEM FOR GAMEPLAY:
    This function is used during gameplay to display the camera feed.
    The horizontal flip creates a mirror effect that users expect.
    Game areas (start, finish, vision) are stored in original camera frame coordinates
    and are drawn BEFORE this flip is applied, so they appear in the correct positions
    after the flip.
    
    Parameters:
    frame (np.ndarray): The OpenCV frame to convert.
    view_port (tuple): The view port for the webcam (width, height).
    Returns:
    pygame.Surface: The PyGame surface.
    """
    # Step 1: Resize using cv2.resize (optimized for images, much faster than scipy zoom)
    resized = cv2.resize(frame, view_port)
    
    # Step 2: Horizontal flip using numpy (faster than cv2.flip)
    flipped = resized[:, ::-1]
    
    # Step 3: 90° counterclockwise rotation using numpy (faster than cv2.rotate)
    rotated = np.rot90(flipped, k=1)
    
    # Step 4: BGR to RGB conversion using numpy slice
    rgb_frame = rotated[:, :, ::-1]
    
    # Step 5: Use make_surface (it's already optimized for this use case)
    return pygame.surfarray.make_surface(rgb_frame)
