from Player import Player
import numpy as np
import supervision as sv
import cv2
from abc import ABC, abstractmethod


class BasePlayerTracker:
    def __init__(self):
        self.previous_result: list[Player] = []
        self.confidence = 0.5

    def yolo_to_supervision(self, yolo_results, ratios: tuple[float, float]) -> sv.Detections:
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
                    x1, x2 = x1 * ratios[0], x2 * ratios[0]
                    y1, y2 = y1 * ratios[1], y2 * ratios[1]
                    track_id = int(box.id[0].cpu().numpy()) if box.id is not None else None
                    detections.append([x1, y1, x2, y2, conf, track_id])

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

    def preprocess_frame(self, frame: cv2.UMat, target_size: tuple[int, int] = (640, 480)) -> cv2.UMat:
        """
        Preprocesses a frame to enhance YOLO object detection performance.

        Args:
            frame (cv2.UMat): Input image (BGR format from OpenCV).
            target_size (tuple[int, int]): Desired frame size for YOLO model.

        Returns:
            cv2.UMat: Preprocessed frame.
        """

        # Resize the frame to match YOLO's expected input size
        frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)

        # Apply Gaussian Blur to reduce noise
        # frame = cv2.GaussianBlur(frame, (5, 5), 0)

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

        return frame

    @abstractmethod
    def process_frame(self, frame: cv2.UMat) -> list[Player]:
        pass
