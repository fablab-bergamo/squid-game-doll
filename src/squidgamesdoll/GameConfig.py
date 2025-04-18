import cv2
import pygame


class GameConfig:
    def __init__(self):
        self._finish_line: tuple[tuple[int, int], tuple[int, int]] = ((0, 0), (0, 0))
        self._starting_line: tuple[tuple[int, int], tuple[int, int]] = ((0, 0), (0, 0))
        self._excl_rects: list[pygame.Rect] = []
        self._exposure_corr: int = 0
        self._current_point = None
        self._video_feed_pos: tuple[int, int] = (0, 0)
        self._video_feed: pygame.Surface = None

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

    def get_rects_scaled(self, video_size: tuple[int, int]) -> list[pygame.Rect]:
        from math import isclose

        ratio = video_size[0] / self._video_feed.get_width()
        if isclose(ratio, video_size[1] / self._video_feed.get_height(), rel_tol=0.01):
            return self.get_rects_scaled(ratio)
        raise ValueError(
            f"Aspect ratio mismatch between video feed ({video_size}) and video size ({self._video_feed.get_size()})"
        )

    def get_rects_scaled(self, ratio: float) -> list[pygame.Rect]:
        result = []
        for r in self._excl_rects:
            rect = pygame.Rect(left=r.left * ratio, top=r.top * ratio, width=r.width * ratio, height=r.height * ratio)
            result.append(rect)
        return result

    def set_screen_config(self, video_feed: pygame.Surface, video_feed_pos: tuple[int, int]):
        self._video_feed = video_feed
        self._video_feed_pos = video_feed_pos

    def config_callback(
        self,
        event: pygame.event,
    ) -> bool:
        relative_pos = (event.pos[0] - self._video_feed_pos[0], event.pos[1] - self._video_feed_pos[1])
        if (
            relative_pos[0] < 0
            or relative_pos[0] > self._video_feed.get_width()
            or relative_pos[1] < 0
            or relative_pos[1] > self._video_feed.get_height()
        ):
            print("Click outside video feed boundaries")
        else:
            if self._current_point is None:
                self._current_point = relative_pos
            else:
                width = relative_pos[0] - self._current_point[0]
                height = relative_pos[1] - self._current_point[1]
                if width > 0 and height > 0:
                    rect = pygame.Rect(
                        left=self._current_point[0], top=self._current_point[1], width=width, height=height
                    )
                    self.add_rect(rect)
                self._current_point = None
        return True
