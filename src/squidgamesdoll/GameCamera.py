import cv2
import numpy as np
from time import sleep
from cv2_enumerate_cameras import enumerate_cameras


class GameCamera:
    @staticmethod
    def getCameraIndex(preferred_idx: int = -1) -> int:
        index = -1
        print("Listing webcams:")
        for camera_info in enumerate_cameras():
            print(f"\t {camera_info.index}: {camera_info.name}")
            if (
                camera_info.name == "HD Pro Webcam C920"
                or camera_info.name == "Logi C270 HD WebCam"
                or camera_info.name == "Webcam C170: Webcam C170"
            ):
                index = camera_info.index
            if camera_info.index == preferred_idx:
                return preferred_idx
        return index

    def __init__(self, index: int = -1):
        """
        Initializes the Camera object with the given webcam index.

        Parameters:
        index (int): The index of the webcam to use.
        """
        if index == -1:
            # Try to find
            index = GameCamera.getCameraIndex(index)
            if index != -1:
                print("Trying with webcam idx", index)

        self.cap = self.__setup_webcam(index)

        if not self.cap.isOpened():
            print(f"Failure opening webcam idx {index}")
            self.valid = False
        else:
            self.valid = True

        self.exposure = -1

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
        frame = self.read_resize()
        if frame is None:
            print("Error: Unable to capture frame.")
            return

        # Convert from RGB to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Extract the value channel
        value_channel = hsv[:, :, 2]

        # Compute the average brightness
        avg_value = np.mean(value_channel)

        # Define threshold (30% of max value 255)
        AIV1 = 0.3 * 255

        current_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)

        # Adjust exposure if the average value is too high
        while avg_value > AIV1:
            new_exposure = max(current_exposure - 1, -16)  # Adjust exposure step (limit to -10 for safety)
            self.set_exposure(new_exposure)
            print(f"Exposure adjusted: {current_exposure} -> {new_exposure}")
            frame = self.read_resize()
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            value_channel = hsv[:, :, 2]
            avg_value = np.mean(value_channel)
            current_exposure = new_exposure
            if new_exposure <= -16:
                break

        print(f"Exposure adjusted: 1/{ int(2**(-1*current_exposure))}")
        self.exposure = current_exposure

    @staticmethod
    def get_native_resolution(idx: int) -> tuple[int, int]:
        for camera_info in enumerate_cameras():
            if idx == camera_info.index:
                if "HD Pro Webcam C920" in camera_info.name:
                    return (1920, 1080)
                elif "Logi C270 HD WebCam" in camera_info.name:
                    return (1280, 720)
                elif "Webcam C170" in camera_info.name:
                    return (1024, 768)
                else:
                    print("Returning default resolution for webcam", camera_info.name)
                    return (1024, 768)
        print("Invalid index for camera resolution", idx)
        return None

    def set_exposure(self, exposure: int):
        """
        Sets the exposure for the given video capture device.

        Parameters:
        cap (cv2.VideoCapture): The video capture device.
        exposure (int): The exposure value to set.
        """
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)  # auto mode
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # manual mode
        self.cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
        self.exposure = exposure
        sleep(0.5)

    def __setup_webcam(self, index: int) -> cv2.VideoCapture:
        """
        Sets up the webcam with the given index and returns the video capture object.

        Parameters:
        index (int): The index of the webcam to use.

        Returns:
        cv2.VideoCapture: The video capture object for the webcam.
        """
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        resolution = GameCamera.get_native_resolution(index)
        if resolution is None:
            raise ValueError("Invalid camera index", index)
        else:
            print("Using webcam resolution", resolution)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        cap.set(cv2.CAP_PROP_FPS, 10.0)
        cap.read()
        return cap

    def isOpened(self) -> bool:
        return self.cap.isOpened()

    def read(self) -> tuple[bool, cv2.UMat]:
        return self.cap.read()

    def read_resize(self) -> cv2.UMat:
        if not self.isOpened():
            return None

        res, frame = self.cap.read()
        if res:
            height, width, _ = frame.shape
            return cv2.resize(frame, (960, 540))

        return None
