import mediapipe as mp
import cv2
from .constants import PLAYER_SIZE


class FaceExtractor:
    def __init__(self):
        # Mediapipe Face Detector
        self.face_detector = mp.solutions.face_detection.FaceDetection(min_detection_confidence=0.4)
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

        # Convert to RGB for Mediapipe
        rgb_face = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)

        # Detect faces
        results = self.face_detector.process(rgb_face)

        if results.detections:
            for detection in results.detections:
                # Get face bounding box relative to the cropped person
                bboxC = detection.location_data.relative_bounding_box
                fx, fy, fw, fh = bboxC.xmin, bboxC.ymin, bboxC.width, bboxC.height

                # Convert relative coordinates to absolute
                h, w, _ = person_crop.shape
                fx, fy, fw, fh = int(fx * w), int(fy * h), int(fw * w), int(fh * h)

                # **Increase space around the face**
                margin = 0.3  # 30% margin
                extra_w = int(fw * margin)
                extra_h = int(fh * margin)

                # New bounding box with margin, ensuring it stays within image bounds
                x_start = max(fx - extra_w, 0)
                y_start = max(fy - extra_h, 0)
                x_end = min(fx + fw + extra_w, w)
                y_end = min(fy + fh + extra_h, h)

                # Extract expanded face region
                face_crop = person_crop[y_start:y_end, x_start:x_end]

                face_crop = cv2.resize(face_crop, (PLAYER_SIZE, PLAYER_SIZE), interpolation=cv2.INTER_AREA)  # Resize

                # **Enhance contrast**
                alpha = 1.8  # Contrast factor (adjustable)
                beta = 9  # Brightness factor (adjustable)
                face_crop = cv2.convertScaleAbs(face_crop, alpha=alpha, beta=beta)
                self._memory[id] = face_crop
                return face_crop

        if id in self._memory:
            return self._memory[id]

        return None
