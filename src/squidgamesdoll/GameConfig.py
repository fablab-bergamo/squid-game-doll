import cv2
import pygame


class GameConfig:
    def __init__(self):
        self._finish_line: tuple[tuple[int, int], tuple[int, int]] = ((0, 0), (0, 0))
        self._starting_line: tuple[tuple[int, int], tuple[int, int]] = ((0, 0), (0, 0))
        self._excl_rects: list[pygame.Rect] = []
        self._exposure_corr: int = 0

    def set_exposure_corr(self, correction: int):
        self._exposure_corr = correction

    def get_exposure_corr(self) -> int:
        return self._exposure_corr

    def set_finish_line(self, line: tuple[tuple[int, int], tuple[int, int]]):
        self._finish_line = line

    def get_finish_line(self) -> tuple[tuple[int, int], tuple[int, int]]:
        return self._finish_line

    def set_starting_line(self, line: tuple[tuple[int, int], tuple[int, int]]):
        self._starting_line = line

    def get_starting_line(self) -> tuple[tuple[int, int], tuple[int, int]]:
        return self._starting_line

    def add_rect(self, excl_rect: pygame.Rect) -> list[pygame.Rect]:
        self._excl_rects.append(excl_rect)
        return self._excl_rects

    def get_rects(self) -> list[pygame.Rect]:
        return self._excl_rects

    def get_rects_scaled(self, ratio: float) -> list[pygame.Rect]:
        result = []
        for r in self._excl_rects:
            rect = pygame.Rect(left=r.left * ratio, top=r.top * ratio, width=r.width * ratio, height=r.height * ratio)
            result.append(rect)
        return result
