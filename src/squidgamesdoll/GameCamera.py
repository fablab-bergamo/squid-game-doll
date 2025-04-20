import cv2
import numpy as np
from time import sleep
from cv2_enumerate_cameras import enumerate_cameras
import platform
import threading
import sys
from GameSettings import GameSettings
from pygame import Rect


class GameCamera:
    @staticmethod
    def getCameraIndex(preferred_idx: int = -1) -> int:
        index = -1
        print(f"Listing webcams with capabilities:{GameCamera.get_cv2_cap()}:")
        for camera_info in enumerate_cameras(GameCamera.get_cv2_cap()):
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
        self.index = index
        self.lock = threading.Lock()

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
        AIV1 = 0.3 * 255

        current_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)

        # Adjust exposure if the average value is too high
        while avg_value > AIV1:
            new_exposure = max(current_exposure - 1, -16)  # Adjust exposure step (limit to -10 for safety)
            self.set_exposure(new_exposure)
            print(f"Exposure adjusted: {current_exposure} -> {new_exposure} (AVG={avg_value})")
            ret, frame = self.read()
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
        for camera_info in enumerate_cameras(GameCamera.get_cv2_cap()):
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

    @staticmethod
    def get_cv2_cap() -> int:
        cap = cv2.CAP_V4L2
        if platform.system() != "Linux":
            cap = cv2.CAP_DSHOW
        return cap

    def __setup_webcam(self, index: int) -> cv2.VideoCapture:
        """
        Sets up the webcam with the given index and returns the video capture object.

        Parameters:
        index (int): The index of the webcam to use.

        Returns:
        cv2.VideoCapture: The video capture object for the webcam.
        """

        cap = cv2.VideoCapture(index, GameCamera.get_cv2_cap())
        # Must set first the codec, then the rest
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc("M", "J", "P", "G"))

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        resolution = GameCamera.get_native_resolution(index)
        if resolution is None:
            raise ValueError("Invalid camera index", index)
        else:
            print("Using webcam resolution", resolution)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # turn the autofocus off
        try:
            codec = int(cap.get(cv2.CAP_PROP_FOURCC)).to_bytes(4, byteorder=sys.byteorder).decode()
            print("\tWebcam codec: ", codec)
        except:
            pass
        format = cap.get(cv2.CAP_PROP_FORMAT)
        print("\tWebcam frame format: ", format)

        return cap

    def isOpened(self) -> bool:
        self.lock.acquire()
        try:
            return self.cap.isOpened()
        finally:
            self.lock.release()

    def read(self) -> tuple[bool, cv2.UMat]:
        self.lock.acquire()
        try:
            return self.cap.read()
        finally:
            self.lock.release()

    def reinit(self) -> bool:
        self.lock.acquire()
        try:
            print("Reinit webcam", self.index)
            if self.cap.isOpened():
                self.cap.release()

            self.cap = None
            self.cap = self.__setup_webcam(self.index)
            return self.isOpened()
        finally:
            self.lock.release()

    @staticmethod
    def bounding_rectangle(rect_list: list[Rect]) -> Rect:
        """
        Compute and return a pygame.Rect that is the bounding rectangle covering
        all rectangles in rect_list. If rect_list is empty, return None.
        """
        if not rect_list:
            return None
        x_min = min(rect.left for rect in rect_list)
        y_min = min(rect.top for rect in rect_list)
        x_max = max(rect.right for rect in rect_list)
        y_max = max(rect.bottom for rect in rect_list)
        return Rect(x_min, y_min, x_max - x_min, y_max - y_min)

    def read_nn(self, settings: GameSettings, max_size: int) -> tuple[cv2.UMat, cv2.UMat, Rect]:
        """
        Read a frame from the webcam, apply a mask based on the vision area defined in settings,
        and return the processed frame along with the original frame and the bounding rectangle in original frame coordinates.

        Parameters:
        settings (GameSettings): The game settings containing the vision area.
        max_size (int): The maximum size in pixel for resizing the frame. Should match the NN input size.

        Returns:
        tuple[cv2.UMat, cv2.UMat, Rect]: The processed frame, original frame, and bounding rectangle.
        """

        ret, nn_frame = self.read()
        original_frame = nn_frame.copy()
        if not ret:
            print("Error: Unable to capture frame.")
            return (None, None, Rect(0, 0, 0, 0))

        # Get the bounding rectangle of the vision area
        rectangles = settings.areas["vision"]
        reference_surface = settings.get_reference_frame()
        bounding_rect = GameCamera.bounding_rectangle(rectangles)

        # We need to zero frame areas outside the list of rectangles in vision_area
        # Let's create a mask for the vision area
        mask = cv2.cvtColor(nn_frame, cv2.COLOR_BGR2GRAY)
        mask[:] = 0  # Initialize mask to zero
        for rect in rectangles:
            # Convert rect coordinates to frame coordinates
            x = int(rect.x / reference_surface.w * nn_frame.shape[1])
            y = int(rect.y / reference_surface.h * nn_frame.shape[0])
            w = int(rect.width / reference_surface.w * nn_frame.shape[1])
            h = int(rect.height / reference_surface.h * nn_frame.shape[0])
            # webcam surface is mirrored-flipped, so we need to adjust the x coordinate for cropping correctly
            x = nn_frame.shape[1] - (x + w)  # Adjust x coordinate for mirrored image
            # Draw the rectangle on the mask
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

        # Apply the mask to the frame
        nn_frame = cv2.bitwise_and(nn_frame, nn_frame, mask=mask)

        # Compute proportions relative to the webcam Sruf, and then apply to the raw CV2 frame
        x_ratio = bounding_rect.x / reference_surface.w
        y_ratio = bounding_rect.y / reference_surface.h
        w_ratio = bounding_rect.width / reference_surface.w
        h_ratio = bounding_rect.height / reference_surface.h
        # Apply the bounding rectangle to the webcam surface
        x = int(x_ratio * nn_frame.shape[1])
        y = int(y_ratio * nn_frame.shape[0])
        w = int(w_ratio * nn_frame.shape[1])
        h = int(h_ratio * nn_frame.shape[0])

        # webcam surface is mirrored-flipped, so we need to adjust the x coordinate for cropping correctly
        x = nn_frame.shape[1] - (x + w)  # Adjust x coordinate for mirrored image
        nn_frame = nn_frame[y : y + h, x : x + w]  # Crop the frame to the bounding rectangle

        if settings.params.get("img_normalization", False):
            # Normalize brightness and contrast using histogram equalization
            lab = cv2.cvtColor(nn_frame, cv2.COLOR_BGR2LAB)  # Convert to LAB color space
            l, a, b = cv2.split(lab)
            l = cv2.equalizeHist(l)  # Apply histogram equalization to the L channel
            lab = cv2.merge((l, a, b))
            nn_frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)  # Convert back to BGR

        if settings.params.get("img_brightness", False):
            # Adjust brightness & contrast (fine-tuning)
            alpha = 1.2  # Contrast control (1.0-3.0)
            beta = 20  # Brightness control (0-100)
            nn_frame = cv2.convertScaleAbs(nn_frame, alpha=alpha, beta=beta)

        # Resize the frame to match NN expected input size
        # but keep the aspect ratio
        # Get original frame dimensions
        video_h, video_w = nn_frame.shape[:2]
        # Calculate the aspect ratio
        aspect_ratio = video_w / video_h
        # Calculate the new dimensions while maintaining the aspect ratio
        if aspect_ratio > 1:
            new_w = max_size
            new_h = int(max_size / aspect_ratio)
        else:
            new_h = max_size
            new_w = int(max_size * aspect_ratio)

        nn_frame = cv2.resize(nn_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return (nn_frame, original_frame, Rect(x, y, w, h))

    @staticmethod
    def intersect(rect: Rect, rect_list: list[Rect]) -> bool:
        """
        Check if a rectangle intersects with any rectangle in a list.

        Parameters:
        rect (Rect): The rectangle to check for intersection.
        rect_list (list[Rect]): The list of rectangles to check against.

        Returns:
        bool: True if there is an intersection, False otherwise.
        """
        for r in rect_list:
            if rect.colliderect(r):
                return True
        return False
