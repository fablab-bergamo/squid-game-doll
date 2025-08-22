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

            # **Enhanced face processing for better visual quality**
            face_crop = self._enhance_face_appearance(face_crop)
            self._memory[id] = face_crop
            return face_crop

        if id in self._memory:
            return self._memory[id]

        return None

    def _enhance_face_appearance(self, face_crop):
        """
        Clean face processing with better background removal and contrast enhancement.
        """
        # 1. Create better face mask using skin color and contour detection
        face_mask = self._create_advanced_face_mask(face_crop)
        
        # 2. Enhance contrast but keep it natural
        alpha = 1.3  # Moderate contrast
        beta = 10    # Slight brightness boost
        face_enhanced = cv2.convertScaleAbs(face_crop, alpha=alpha, beta=beta)
        
        # 3. Create clean background (pure black for dramatic effect)
        h, w = face_crop.shape[:2]
        background = np.zeros_like(face_crop, dtype=np.uint8)
        
        # 4. Apply mask with smooth blending
        face_mask_3d = np.stack([face_mask] * 3, axis=2).astype(np.float32) / 255.0
        
        # Blend face with clean black background
        face_result = (face_enhanced * face_mask_3d + background * (1 - face_mask_3d)).astype(np.uint8)
        
        return face_result
    
    def _create_advanced_face_mask(self, face_crop):
        """
        Create a better face mask using skin color detection and morphological operations.
        """
        h, w = face_crop.shape[:2]
        
        # Method 1: Skin color detection in HSV space
        hsv = cv2.cvtColor(face_crop, cv2.COLOR_BGR2HSV)
        
        # Define skin color range in HSV (covers most skin tones)
        lower_skin = np.array([0, 20, 70])
        upper_skin = np.array([20, 255, 255])
        skin_mask1 = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Additional skin range for different lighting
        lower_skin2 = np.array([0, 48, 80])
        upper_skin2 = np.array([20, 255, 255])
        skin_mask2 = cv2.inRange(hsv, lower_skin2, upper_skin2)
        
        # Combine skin masks
        skin_mask = cv2.bitwise_or(skin_mask1, skin_mask2)
        
        # Method 2: Create elliptical base mask as fallback
        base_mask = np.zeros((h, w), dtype=np.uint8)
        center = (w//2, h//2)
        axes = (int(w*0.4), int(h*0.5))  # More conservative ellipse
        cv2.ellipse(base_mask, center, axes, 0, 0, 360, 255, -1)
        
        # Combine skin detection with elliptical mask
        combined_mask = cv2.bitwise_and(skin_mask, base_mask)
        
        # Fill holes and smooth the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        
        # If skin detection failed, fall back to elliptical mask
        if cv2.countNonZero(combined_mask) < (h * w * 0.05):  # Less than 5% of image
            combined_mask = base_mask
        
        # Smooth the edges for natural blending
        combined_mask = cv2.GaussianBlur(combined_mask, (15, 15), 5)
        
        return combined_mask
