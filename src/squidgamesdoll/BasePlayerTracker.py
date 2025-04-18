from Player import Player
import numpy as np
import supervision as sv
import cv2
from abc import ABC, abstractmethod
from GameSettings import GameSettings
from GameScreen import GameScreen
import pygame


class BasePlayerTracker:
    def __init__(self):
        self.previous_result: list[Player] = []
        self.confidence = 0.5
        self.vision_rect = pygame.Rect(0, 0, 0, 0)
        self.nn_rect = pygame.Rect(0, 0, 0, 0)
        self.frame_rect = pygame.Rect(0, 0, 0, 0)

    def yolo_to_supervision(self, yolo_results) -> sv.Detections:
        """
        Converts YOLO results into a supervision Detections object with proper scaling.
        """
        detections = []
        for result in yolo_results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                conf = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())
                if conf > self.confidence and class_id == 0:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    rect = pygame.Rect(x1, y1, x2 - x1, y2 - y1)
                    # Adjust the coordinates 0..1 to match the original NN frame size
                    conv_rect = GameScreen.convert_coord(rect, pygame.Rect(0, 0, 1, 1), self.nn_rect)
                    # Now convert from NN frame to the vision frame size
                    conv_rect = GameScreen.convert_coord(rect, self.nn_rect, self.vision_rect)
                    # Now convert from NN frame to the vision frame size
                    conv_rect = GameScreen.convert_coord(rect, self.vision_rect, self.frame_rect)

                    track_id = int(box.id[0].cpu().numpy()) if box.id is not None else None
                    detections.append(
                        [
                            conv_rect.x,
                            conv_rect.y,
                            conv_rect.x + conv_rect.w,
                            conv_rect.y + conv_rect.h,
                            conf,
                            track_id,
                        ]
                    )

        if not detections:
            return sv.Detections.empty()

        detections = np.array(detections)
        return sv.Detections(xyxy=detections[:, :4], confidence=detections[:, 4], tracker_id=detections[:, 5])

    def supervision_to_players(self, detections: sv.Detections) -> list[Player]:
        """
        Converts a supervision Detections object into a list of Player objects.
        """
        players = []
        for i in range(len(detections.xyxy)):
            x1, y1, x2, y2 = map(int, detections.xyxy[i])
            track_id = int(detections.tracker_id[i]) if detections.tracker_id[i] is not None else None
            players.append(Player(track_id, (x1, y1, x2, y2)))
        return players

    def bounding_rectangle(self, rect_list):
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
        return pygame.Rect(x_min, y_min, x_max - x_min, y_max - y_min)

    def apply_vision_frame(
        self, rectangles: list[pygame.Rect], reference_surface: list[int, int], webcam_frame: cv2.UMat
    ) -> tuple[cv2.UMat, pygame.Rect]:
        # Get the bounding rectangle of the vision area
        bounding_rect = self.bounding_rectangle(rectangles)
        if bounding_rect:
            # We need to zero frame areas outside the list of rectangles in vision_area
            # Let's create a mask for the vision area
            mask = cv2.cvtColor(webcam_frame, cv2.COLOR_BGR2GRAY)
            mask[:] = 0  # Initialize mask to zero
            for rect in rectangles:
                # Convert rect coordinates to frame coordinates
                x = int(rect.x / reference_surface[0] * webcam_frame.shape[1])
                y = int(rect.y / reference_surface[1] * webcam_frame.shape[0])
                w = int(rect.width / reference_surface[0] * webcam_frame.shape[1])
                h = int(rect.height / reference_surface[1] * webcam_frame.shape[0])
                # webcam surface is mirrored-flipped, so we need to adjust the x coordinate for cropping correctly
                x = webcam_frame.shape[1] - (x + w)  # Adjust x coordinate for mirrored image
                # Draw the rectangle on the mask
                cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

            # Apply the mask to the frame
            webcam_frame = cv2.bitwise_and(webcam_frame, webcam_frame, mask=mask)

            # Compute proportions relative to the webcam Sruf, and then apply to the raw CV2 frame
            x_ratio = bounding_rect.x / reference_surface[0]
            y_ratio = bounding_rect.y / reference_surface[1]
            w_ratio = bounding_rect.width / reference_surface[0]
            h_ratio = bounding_rect.height / reference_surface[1]
            # Apply the bounding rectangle to the webcam surface
            x = int(x_ratio * webcam_frame.shape[1])
            y = int(y_ratio * webcam_frame.shape[0])
            w = int(w_ratio * webcam_frame.shape[1])
            h = int(h_ratio * webcam_frame.shape[0])

            # webcam surface is mirrored-flipped, so we need to adjust the x coordinate for cropping correctly
            x = webcam_frame.shape[1] - (x + w)  # Adjust x coordinate for mirrored image
            webcam_frame = webcam_frame[y : y + h, x : x + w]  # Crop the frame to the bounding rectangle

            return (webcam_frame, pygame.Rect(x, y, w, h))
        # Feed the full frame otherwise
        return (None, pygame.Rect(0, 0, 0, 0))

    def preprocess_frame(self, frame: cv2.UMat, gamesettings: GameSettings, model_size=tuple[int, int]) -> cv2.UMat:
        """
        Preprocesses a frame to enhance YOLO object detection performance.

        Args:
            frame (cv2.UMat): Input image (BGR format from OpenCV).
            target_size (tuple[int, int]): Desired frame size for YOLO model.

        Returns:
            cv2.UMat: Preprocessed frame.
        """

        # Apply crop and masking rectangles
        frame, self.nn_rect = self.apply_vision_frame(
            gamesettings.areas["vision"], gamesettings.reference_frame, frame
        )
        self.frame_rect = pygame.Rect(0, 0, frame.shape[1], frame.shape[0])
        
        # Apply Gaussian Blur to reduce noise
        # frame = cv2.GaussianBlur(frame, (5, 5), 0)

        if gamesettings.settings.get("img_normalization", False):
            # Normalize brightness and contrast using histogram equalization
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)  # Convert to LAB color space
            l, a, b = cv2.split(lab)
            l = cv2.equalizeHist(l)  # Apply histogram equalization to the L channel
            lab = cv2.merge((l, a, b))
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)  # Convert back to BGR

        # Adjust brightness & contrast (fine-tuning)
        alpha = 1.2  # Contrast control (1.0-3.0)
        beta = 20  # Brightness control (0-100)
        frame = cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

        # Resize the frame to match NN expected input size
        # but keep the aspect ratio
        # Get original frame dimensions
        video_h, video_w = frame.shape[:2]
        # Calculate the aspect ratio
        aspect_ratio = video_w / video_h
        # Calculate the new dimensions while maintaining the aspect ratio
        if aspect_ratio > 1:
            new_w = model_size[0]
            new_h = int(model_size[0] / aspect_ratio)
        else:
            new_h = model_size[1]
            new_w = int(model_size[1] * aspect_ratio)
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        self.nn_rect = pygame.Rect(0, 0, new_w, new_h)
        return frame

    @abstractmethod
    def process_frame(self, frame: cv2.UMat, gamesettings: GameSettings) -> list[Player]:
        pass

    @abstractmethod
    def get_sample_frame(self, frame: cv2.UMat, gamesettings: GameSettings) -> cv2.UMat:
        pass
