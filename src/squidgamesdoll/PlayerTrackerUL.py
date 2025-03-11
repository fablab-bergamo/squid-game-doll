import cv2
from ultralytics import YOLO
from Player import Player
import torch
from BasePlayerTracker import BasePlayerTracker


class PlayerTrackerUL(BasePlayerTracker):
    def __init__(self, model_path: str = "yolov8m.pt") -> None:
        """
        Initialize the PlayerTracker with the given YOLO model.

        Args:
            model_path (str): Path to the YOLO model.
            movement_threshold (int): Pixels of movement to be considered "moving".
        """
        super().__init__()
        self.yolo: YOLO = YOLO(model_path, verbose=False)
        # Run the model on the Nvidia GPU
        if torch.cuda.is_available():
            self.yolo.to("cuda")

        print(f"YOLOv8 running on {self.yolo.device}")

    def process_frame(self, frame: cv2.UMat) -> list[Player]:
        """
        Processes a video frame, detects players using YOLO, and returns a list of Player objects.

        Args:
            frame (cv2.UMat): The current video frame.

        Returns:
            list[Player]: List of detected Player objects.
        """
        try:
            # Preprocess the frame for improved YOLO detection
            h, w = frame.shape[:2]
            target_size = (640, int(640 / (w / h)))
            ratios = (w / target_size[0], h / target_size[1])
            yolo_frame = self.preprocess_frame(frame, target_size)
            results = self.yolo.track(yolo_frame, persist=True, stream=True, classes=[0])
        except Exception as e:
            print("Error:", e)
            return self.previous_result

        detections = self.yolo_to_supervision(results, ratios)
        players = self.supervision_to_players(detections)
        for p in players:
            print(p)
        self.previous_result = players
        return players
