import cv2
import torch
from ultralytics import YOLO
from pygame import Rect
from loguru import logger

from .BasePlayerTracker import BasePlayerTracker
from .GameSettings import GameSettings
from .Player import Player


class PlayerTrackerUL(BasePlayerTracker):
    def __init__(self, model_path: str = "yolo11x.pt") -> None:
        """
        Initialize the PlayerTracker with the given YOLO model.

        Args:
            model_path (str): Path to the YOLO model.
            movement_threshold (int): Pixels of movement to be considered "moving".
        """
        super().__init__()
        self.model_path = model_path
        self.yolo: YOLO = YOLO(self.model_path, verbose=False)
        # Run the model on the Nvidia GPU
        if torch.cuda.is_available():
            self.yolo.to("cuda")

        logger.info(f"YOLOv8 running on {self.yolo.device}")

    def reset(self) -> None:
        """
        Resets the player tracker to its initial state.
        """
        self.previous_result = []
        self.yolo: YOLO = YOLO(self.model_path, verbose=False)
        # Run the model on the Nvidia GPU
        if torch.cuda.is_available():
            self.yolo.to("cuda")

        logger.info(f"YOLOv8 running on {self.yolo.device}")

    def process_nn_frame(self, nn_frame: cv2.UMat, gamesettings: GameSettings) -> list[Player]:
        """
        Processes a video frame, detects players using YOLO, and returns a list of Player objects.

        Args:
            frame (cv2.UMat): The current video frame.

        Returns:
            list[Player]: List of detected Player objects.
        """
        start_time = cv2.getTickCount()
        try:
            self.frame_rect = Rect(0, 0, nn_frame.shape[1], nn_frame.shape[0])
            self.nn_rect = Rect(0, 0, nn_frame.shape[1], nn_frame.shape[0])
            results = self.yolo.track(nn_frame, persist=True, stream=True, classes=[0])
        except Exception as e:
            logger.exception("process_nn_frame: error:")
            return self.previous_result

        # Apply confidence threshold from settings
        self.confidence = gamesettings.params.get("confidence", 40) / 100.0
        detections = self.yolo_to_supervision(results)
        players = self.supervision_to_players(detections)
        for p in players:
            logger.debug(p)
        self.previous_result = players
        end_time = cv2.getTickCount()
        time_taken = (end_time - start_time) / cv2.getTickFrequency()
        self.fps = 1 / time_taken if time_taken > 0 else 0
        return players

    def get_max_size(self) -> int:
        return 640
