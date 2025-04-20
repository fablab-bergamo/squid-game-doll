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
        self.fps = 0.0

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
                    print("Y2S : (x1, y1, x2, y2)", (x1, y1, x2, y2))

                    x1 = int(x1 * self.frame_rect.width / self.nn_rect.width + self.nn_rect.x)
                    y1 = int(y1 * self.frame_rect.height / self.nn_rect.height + self.nn_rect.y)
                    x2 = int(x2 * self.frame_rect.width / self.nn_rect.width + self.nn_rect.x)
                    y2 = int(y2 * self.frame_rect.height / self.nn_rect.height + self.nn_rect.y)
                    print("Y2S -> (x1, y1, x2, y2)", (x1, y1, x2, y2), "nn_rect", self.nn_rect)
                    conv_rect = pygame.Rect(x1, y1, x2 - x1, y2 - y1)
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

    @abstractmethod
    def process_frame(self, frame: cv2.UMat, gamesettings: GameSettings) -> list[Player]:
        pass

    @abstractmethod
    def process_nn_frame(self, nn_frame: cv2.UMat, gamesettings: GameSettings) -> list[Player]:
        pass

    @abstractmethod
    def reset(self):
        pass

    def get_fps(self) -> float:
        return round(self.fps, 1)
