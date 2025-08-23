import cv2
import numpy as np
from .constants import PLAYER_SIZE
from .cuda_utils import cuda_cvt_color, cuda_resize, is_cuda_opencv_available


class FaceExtractor:
    def __init__(self):
        # OpenCV Haar Cascade Face Detector
        try:
            # Try standard OpenCV data path
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_detector = cv2.CascadeClassifier(cascade_path)
        except AttributeError:
            # Fallback for custom OpenCV builds without cv2.data
            import os
            cascade_paths = [
                '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
                '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
                '/opt/opencv/data/haarcascades/haarcascade_frontalface_default.xml'
            ]
            cascade_path = None
            for path in cascade_paths:
                if os.path.exists(path):
                    cascade_path = path
                    break
            
            if cascade_path:
                self.face_detector = cv2.CascadeClassifier(cascade_path)
                print(f"✅ Using Haar cascade from: {cascade_path}")
            else:
                raise RuntimeError("Could not find haarcascade_frontalface_default.xml. Please install opencv-data package.")
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

        # Convert to grayscale for OpenCV Haar cascades (GPU accelerated if available)
        gray_face = cuda_cvt_color(person_crop, cv2.COLOR_BGR2GRAY)

        # Detect faces using Haar cascades
        faces = self.face_detector.detectMultiScale(
            gray_face,
            scaleFactor=1.3,  # Faster detection (was 1.1)
            minNeighbors=3,   # Faster detection (was 5)
            minSize=(20, 20), # Larger minimum size for better performance
            flags=cv2.CASCADE_SCALE_IMAGE | cv2.CASCADE_DO_CANNY_PRUNING  # Additional optimization
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

            face_crop = cuda_resize(face_crop, (PLAYER_SIZE, PLAYER_SIZE), interpolation=cv2.INTER_AREA)  # GPU-accelerated resize
            
            self._memory[id] = face_crop
            return face_crop

        if id in self._memory:
            return self._memory[id]

        return None

