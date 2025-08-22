import cv2
import numpy as np
from .constants import PLAYER_SIZE


class FaceExtractor:
    def __init__(self):
        # OpenCV Haar Cascade Face Detector
        self.face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self._memory = {}

    def reset_memory(self):
        self._memory = {}

    def extract_face(self, frame: cv2.UMat, bbox: tuple, id: int) -> cv2.UMat:
        """
        Extracts a face from a given person's bounding box.
        Args:
            frame (numpy.ndarray): The input frame.
            bbox (tuple): Bounding box (x1, y1, x2, y2) of the detected player.
        Returns:
            face_crop (numpy.ndarray or None): Cropped face if detected, otherwise None.
        """
        x1, y1, x2, y2 = bbox

        # Crop the person from the frame
        person_crop = frame[y1:y2, x1:x2]

        if person_crop.size == 0:
            return None

        # Convert to grayscale for OpenCV Haar cascades
        gray_face = cv2.cvtColor(person_crop, cv2.COLOR_BGR2GRAY)

        # Detect faces using Haar cascades
        faces = self.face_detector.detectMultiScale(
            gray_face,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        if len(faces) > 0:
            # Get the largest face (most confident detection)
            face = max(faces, key=lambda x: x[2] * x[3])  # Sort by area (w * h)
            fx, fy, fw, fh = face

            # **Increase space around the face**
            margin = 0.3  # 30% margin
            extra_w = int(fw * margin)
            extra_h = int(fh * margin)

            # New bounding box with margin, ensuring it stays within image bounds
            h, w = gray_face.shape
            x_start = max(fx - extra_w, 0)
            y_start = max(fy - extra_h, 0)
            x_end = min(fx + fw + extra_w, w)
            y_end = min(fy + fh + extra_h, h)

            # Extract expanded face region from original color image
            face_crop = person_crop[y_start:y_end, x_start:x_end]

            if face_crop.size == 0:
                return None

            face_crop = cv2.resize(face_crop, (PLAYER_SIZE, PLAYER_SIZE), interpolation=cv2.INTER_AREA)  # Resize
            
            self._memory[id] = face_crop
            return face_crop

        if id in self._memory:
            return self._memory[id]

        return None

