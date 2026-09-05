import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions, RunningMode
from .constants import PLAYER_SIZE, ROOT
from .cuda_utils import cuda_cvt_color, cuda_resize, is_cuda_opencv_available

# Short-range (< 2m) BlazeFace model, bundled locally so face detection works offline.
_FACE_MODEL_PATH = ROOT + "/media/blaze_face_short_range.tflite"


class FaceExtractor:
    def __init__(self):
        # MediaPipe face detector (Google's ultra-fast), new Tasks API
        # (mp.solutions.face_detection was removed in mediapipe >= 0.10.30)
        options = FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=_FACE_MODEL_PATH),
            running_mode=RunningMode.IMAGE,
            min_detection_confidence=0.5,
        )
        self.face_detector = FaceDetector.create_from_options(options)
        print("✅ Using MediaPipe face detector (Google)")
        self._memory = {}

    def reset_memory(self):
        self._memory = {}

    def extract_face(self, frame: cv2.UMat, bbox: tuple, id: int, return_bbox: bool = False):
        """
        Extracts a face from a given person's bounding box.
        Args:
            frame (numpy.ndarray): The input frame.
            bbox (tuple): Bounding box (x1, y1, x2, y2) of the detected player.
            id (int): Player ID for tracking.
            return_bbox (bool): If True, return (face_crop, face_bbox). If False, return just face_crop.
        Returns:
            face_crop (numpy.ndarray or None): Cropped face if detected, otherwise None.
            OR tuple (face_crop, face_bbox) if return_bbox=True, where face_bbox is (x1, y1, w, h) in full frame coordinates.
        """
        x1, y1, x2, y2 = bbox

        # Crop the person from the frame
        person_crop = frame[y1:y2, x1:x2]

        if person_crop.size == 0:
            return None

        # MediaPipe detection (Google's ultra-fast)
        rgb_image = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
        results = self.face_detector.detect(mp_image)

        # Convert MediaPipe format to (x, y, w, h) for compatibility
        # (Tasks API bounding_box is already in absolute pixel coordinates)
        faces = []
        if results.detections:
            for detection in results.detections:
                bbox = detection.bounding_box
                faces.append([bbox.origin_x, bbox.origin_y, bbox.width, bbox.height])

        if len(faces) > 0:
            # Get the largest face (most confident detection)
            face = max(faces, key=lambda x: x[2] * x[3])  # Sort by area (w * h)
            fx, fy, fw, fh = face

            # **Increase space around the face**
            margin = 0.3  # 30% margin
            extra_w = int(fw * margin)
            extra_h = int(fh * margin)

            # New bounding box with margin, ensuring it stays within image bounds
            h, w = person_crop.shape[:2]
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
            
            if return_bbox:
                # Return both face crop and bounding box coordinates in full frame
                # Convert from person crop coordinates to full frame coordinates
                face_bbox_full_frame = (x1 + fx, y1 + fy, fw, fh)
                return face_crop, face_bbox_full_frame
            else:
                return face_crop

        if id in self._memory:
            if return_bbox:
                return self._memory[id], None  # Return cached face with no bbox info
            else:
                return self._memory[id]

        if return_bbox:
            return None, None
        return None

