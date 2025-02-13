import cv2
from time import sleep

EXPECTED_WDIM = 960
EXPECTED_HDIM = 720

def set_exposure(cap: cv2.VideoCapture, exposure: int):
    """
    Sets the exposure for the given video capture device.

    Parameters:
    cap (cv2.VideoCapture): The video capture device.
    exposure (int): The exposure value to set.
    """
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3) # auto mode
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1) # manual mode
    cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
    sleep(1)

def setup_webcam(index: int) -> cv2.VideoCapture:
    """
    Sets up the webcam with the given index and returns the video capture object.

    Parameters:
    index (int): The index of the webcam to use.

    Returns:
    cv2.VideoCapture: The video capture object for the webcam.
    """
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 5.0)
    return cap