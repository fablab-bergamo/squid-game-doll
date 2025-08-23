import numpy as np
import supervision as sv
import cv2
import pygame

from abc import ABC, abstractmethod
from .game_settings import GameSettings
from .player import Player


class BasePlayerTracker:
    def __init__(self):
        self.previous_result: list[Player] = []
        self.confidence = 0.5
        self.vision_rect = pygame.Rect(0, 0, 0, 0)
        self.nn_rect = pygame.Rect(0, 0, 0, 0)
        self.frame_rect = pygame.Rect(0, 0, 0, 0)
        self.fps = 0.0

    def yolo_to_supervision(self, yolo_results) -> sv.Detections:
        """
        Converts YOLO results into a supervision Detections object with proper scaling.
        Optimized to minimize GPU→CPU transfers.
        """
        detections = []
        for result in yolo_results:
            if result.boxes is None:
                continue
            
            # Batch transfer all data from GPU to CPU in one go (MAJOR OPTIMIZATION)
            boxes = result.boxes
            if len(boxes) == 0:
                continue
                
            # Single GPU→CPU transfer for all boxes
            confidences = boxes.conf.cpu().numpy()
            class_ids = boxes.cls.cpu().numpy() 
            xyxy_coords = boxes.xyxy.cpu().numpy()
            track_ids = boxes.id.cpu().numpy() if boxes.id is not None else None

            # Process each detection using CPU arrays (no more GPU transfers)
            for i in range(len(boxes)):
                conf = float(confidences[i])
                class_id = int(class_ids[i])
                
                if conf > self.confidence and class_id == 0:
                    x1, y1, x2, y2 = xyxy_coords[i]
                    x1 = int(x1 * self.frame_rect.width / self.nn_rect.width + self.nn_rect.x)
                    y1 = int(y1 * self.frame_rect.height / self.nn_rect.height + self.nn_rect.y)
                    x2 = int(x2 * self.frame_rect.width / self.nn_rect.width + self.nn_rect.x)
                    y2 = int(y2 * self.frame_rect.height / self.nn_rect.height + self.nn_rect.y)
                    
                    track_id = int(track_ids[i]) if track_ids is not None else None
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
            confidence = float(detections.confidence[i]) if len(detections.confidence) > i else 0.0
            players.append(Player(track_id, (x1, y1, x2, y2), confidence))
        return players

    @abstractmethod
    def process_frame(self, frame: cv2.UMat, gamesettings: GameSettings) -> list[Player]:
        pass

    @abstractmethod
    def process_nn_frame(self, nn_frame: cv2.UMat, gamesettings: GameSettings) -> list[Player]:
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def get_max_size(self) -> int:
        pass

    def get_fps(self) -> float:
        return round(self.fps, 1)
