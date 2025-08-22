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
        Simplified face processing: background removal, contour enhancement, make face stand out.
        """
        # 1. Create face mask for background removal
        face_mask = self._create_simple_face_mask(face_crop)
        
        # 2. Enhance contrast and reduce oversaturation
        alpha = 1.4  # Strong contrast for dramatic effect
        beta = 15    # Brightness boost
        face_enhanced = cv2.convertScaleAbs(face_crop, alpha=alpha, beta=beta)
        
        # 3. Enhance facial contours with edge detection
        gray = cv2.cvtColor(face_enhanced, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Apply edge enhancement
        edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        face_with_edges = cv2.addWeighted(face_enhanced, 0.8, edges_colored, 0.2, 0)
        
        # 4. Remove background with dramatic effect
        # Create 3-channel mask
        face_mask_3d = np.stack([face_mask] * 3, axis=2).astype(np.float32) / 255.0
        
        # Create stylistic background (dark gradient)
        h, w = face_crop.shape[:2]
        background = np.zeros_like(face_crop, dtype=np.uint8)
        # Add subtle dark gradient from edges
        center = (w//2, h//2)
        Y, X = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
        max_dist = np.sqrt(center[0]**2 + center[1]**2)
        gradient = (dist_from_center / max_dist * 40).astype(np.uint8)
        background[:, :, 0] = gradient  # Slight blue tint in background
        background[:, :, 1] = gradient * 0.8
        background[:, :, 2] = gradient * 0.6
        
        # Blend face with stylistic background
        face_result = (face_with_edges * face_mask_3d + background * (1 - face_mask_3d)).astype(np.uint8)
        
        return face_result
    
    def _create_simple_face_mask(self, face_crop):
        """
        Create a simple elliptical mask to isolate the face from background.
        """
        h, w = face_crop.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        # Create elliptical mask covering most of the image (assuming face is centered)
        center = (w//2, h//2)
        axes = (int(w*0.45), int(h*0.45))  # Cover 90% of width/height
        
        cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
        
        # Smooth the edges for better blending
        mask = cv2.GaussianBlur(mask, (21, 21), 10)
        
        return mask
