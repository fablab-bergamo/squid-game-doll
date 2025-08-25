import cv2
import numpy as np
import mediapipe as mp
from .constants import PLAYER_SIZE
from .cuda_utils import cuda_cvt_color, cuda_resize, is_cuda_opencv_available


class FaceExtractor:
    def __init__(self):
        # MediaPipe face detector (Google's ultra-fast)
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detector = self.mp_face_detection.FaceDetection(
            model_selection=0,  # 0 for short-range (< 2m), 1 for full-range
            min_detection_confidence=0.5
        )
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
        results = self.face_detector.process(rgb_image)
        
        # Convert MediaPipe format to (x, y, w, h) for compatibility
        faces = []
        if results.detections:
            h, w = person_crop.shape[:2]
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                # Convert relative coordinates to absolute pixels
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h) 
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                faces.append([x, y, width, height])

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

