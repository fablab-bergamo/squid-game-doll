import cv2
import numpy as np
from time import sleep

class Camera:
    def __init__(self, index: int):
        """
        Initializes the Camera object with the given webcam index.

        Parameters:
        index (int): The index of the webcam to use.
        """
        self.cap = self.__setup_webcam(index)
        self.exposure = -7
    
    def __del__(self):
        """
        Releases the video capture object.
        """
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()

    def getVideoCapture(self) -> cv2.VideoCapture:
        """
        Returns the video capture object.

        Returns:
        cv2.VideoCapture: The video capture object for the webcam.
        """
        return self.cap
    
    def auto_exposure(self):
        """
        Sets the exposure using average brightness
        See https://www.researchgate.net/profile/Stefan-Toth-3/publication/350124875_Laser_spot_detection/links/605289e092851cd8ce4b5945/Laser-spot-detection.pdf
        """
        ret, frame = self.read()
        if not ret:
            print("Error: Unable to capture frame.")
            return
        
        # Convert from RGB to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Extract the value channel
        value_channel = hsv[:, :, 2]
        
        # Compute the average brightness
        avg_value = np.mean(value_channel)
        
        # Define threshold (30% of max value 255)
        AIV1 = 0.3 * 255  # Approximately 77
        
        current_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)

        # Adjust exposure if the average value is too high
        while avg_value > AIV1:
            new_exposure = max(current_exposure - 1, -10)  # Adjust exposure step (limit to -10 for safety)
            self.set_exposure(new_exposure)
            print(f"Exposure adjusted: {current_exposure} -> {new_exposure}")
            _, frame = self.read()
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            value_channel = hsv[:, :, 2]
            avg_value = np.mean(value_channel)
        
        print(f"Exposure adjusted: 1/{ int(2**(-1*current_exposure))}")
        self.exposure = current_exposure
            

    def set_exposure(self, exposure: int):
        """
        Sets the exposure for the given video capture device.

        Parameters:
        cap (cv2.VideoCapture): The video capture device.
        exposure (int): The exposure value to set.
        """
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3) # auto mode
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1) # manual mode
        self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
        self.exposure = exposure
        sleep(0.5)

    def read(self) -> tuple:
        """
        Reads a frame from the video capture device.

        Returns:
        tuple: A tuple containing the return value and the frame.
        """
        return self.cap.read()
    
    def __setup_webcam(self, index: int) -> cv2.VideoCapture:
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
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)
        cap.set(cv2.CAP_PROP_FPS, 10.0)
        return cap