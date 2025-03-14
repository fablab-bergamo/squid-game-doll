import cv2
import pygame
import numpy as np


class Player:
    MOVEMENT_THRESHOLD_PX = 15

    def __init__(self, id: int, coords: tuple):
        self._id = id
        self._coords = coords
        self._face = None
        self._last_position = coords
        self._eliminated = False
        self._visible = False
        self._winner = False

    def is_winner(self) -> bool:
        return self._winner

    def set_winner(self):
        self._winner = True

    def get_id(self) -> int:
        return self._id

    def set_visible(self, visible: bool) -> None:
        self._visible = visible

    def is_visible(self) -> bool:
        return self._visible

    def get_target(self) -> tuple[int, int]:
        rect = self.get_rect()
        """ Target = Half the width, one third height """
        return (rect[0] + rect[2] / 2, rect[1] + rect[3] / 3)

    def set_eliminated(self, eliminated: bool):
        self._eliminated = eliminated

    def is_eliminated(self) -> bool:
        return self._eliminated

    def set_last_position(self, position: tuple):
        self._last_position = position

    def get_last_position(self) -> tuple:
        return self._last_position

    def set_face(self, face: cv2.UMat):
        """Saves the face image of the player"""
        self._face = face

    def get_face(self) -> cv2.UMat:
        """Returns the face image of the player"""
        return self._face

    def get_image(self) -> pygame.image:
        if self._face is None:
            return None
        return pygame.image.frombuffer(self._face.tostring(), self._face.shape[1::-1], "BGR")

    def set_rect(self, rect: tuple):
        """Sets the bounding box rectangle in (x, y, w, h) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        self._coords = (rect[0], rect[1], rect[2] + rect[0], rect[3] + rect[1])

    def get_rect(self):
        """Returns the bounding box rectangle in (x, y, w, h) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        return self.get_rect_from_pos(self._coords)

    def get_last_rect(self) -> tuple:
        """Returns the bounding box rectangle in (x, y, w, h) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        if self._last_position is None:
            return None
        return self.get_rect_from_pos(self._last_position)

    def get_rect_from_pos(self, pos: tuple) -> tuple:
        """Returns the bounding box rectangle in (x, y, w, h) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        return (
            pos[0],
            pos[1],
            pos[2] - pos[0],
            pos[3] - pos[1],
        )

    def get_coords(self):
        """Returns the bounding box coordinates in (x1, y1, x2, y2) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        return self._coords

    def set_coords(self, coords: tuple):
        """Sets the bounding box coordinates in (x1, y1, x2, y2) format
        Note: coordinates are relative to the webcam frame in original dimensions"""
        self._coords = coords

    def has_moved(self):
        """Returns the movement status of the player"""
        if self._last_position is None:
            self._last_position = self._coords
            return False

        x1, y1, x2, y2 = self._coords
        prev_x1, prev_y1, prev_x2, prev_y2 = self._last_position

        # distance between the centers of the two rectangles
        distance = np.linalg.norm(
            [
                (x1 + x2) / 2 - (prev_x1 + prev_x2) / 2,
                (y1 + y2) / 2 - (prev_y1 + prev_y2) / 2,
            ]
        )

        return distance > Player.MOVEMENT_THRESHOLD_PX

    def __str__(self):
        return f"Player {self._id} at {self._coords} (moved: {self.has_moved()})"
