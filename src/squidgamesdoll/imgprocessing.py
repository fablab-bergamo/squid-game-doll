import cv2
from numpy.linalg import norm
import numpy as np


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
    table = np.array(
        [((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]
    ).astype("uint8")
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
