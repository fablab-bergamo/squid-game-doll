import cv2
from ultralytics import YOLO
from Player import Player
import torch
from BasePlayerTracker import BasePlayerTracker
from GameSettings import GameSettings


class PlayerTrackerUL(BasePlayerTracker):
    def __init__(self, model_path: str = "yolo11x.pt") -> None:
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

    def __preprocess(self, frame: cv2.UMat, gamesettings: GameSettings) -> tuple[cv2.UMat, tuple[float, float]]:
        """
        Preprocesses the input frame for YOLO inference.
        """
        yolo_frame = self.preprocess_frame(frame, gamesettings, (640, 640))
        # Get original frame dimensions
        video_h, video_w = frame.shape[:2]
        ratios = (video_w / yolo_frame.shape[1], video_h / yolo_frame.shape[0])
        return yolo_frame, ratios

    def get_sample_frame(self, frame: cv2.UMat, gamesettings: GameSettings) -> cv2.UMat:
        return self.__preprocess(frame, gamesettings)[0]

    def process_frame(self, frame: cv2.UMat, gamesettings: GameSettings) -> list[Player]:
        """
        Processes a video frame, detects players using YOLO, and returns a list of Player objects.

        Args:
            frame (cv2.UMat): The current video frame.

        Returns:
            list[Player]: List of detected Player objects.
        """
        try:
            yolo_frame, ratios = self.__preprocess(frame, gamesettings)
            results = self.yolo.track(yolo_frame, persist=True, stream=True, classes=[0])
        except Exception as e:
            print("Error:", e)
            return self.previous_result

        # Apply confidence threshold from settings
        super().confidence = gamesettings.settings.get("confidence", 40) / 100.0
        detections = self.yolo_to_supervision(results, ratios)
        players = self.supervision_to_players(detections)
        for p in players:
            print(p)
        self.previous_result = players
        return players
