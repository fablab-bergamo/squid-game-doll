import os

# Color constants
GREEN: tuple[int, int, int] = (0, 255, 0)
RED: tuple[int, int, int] = (255, 0, 0)
WHITE: tuple[int, int, int] = (255, 255, 255)
BLACK: tuple[int, int, int] = (0, 0, 0)
YELLOW: tuple[int, int, int] = (255, 255, 0)
DARK_GREEN: tuple[int, int, int] = (3, 122, 118)
LIGHT_GREEN: tuple[int, int, int] = (36, 159, 156)
SALMON: tuple[int, int, int] = (244, 71, 134)
PINK: tuple[int, int, int] = (237, 27, 118)

# Size of each player tile in pixels
PLAYER_SIZE: int = 150
FADE_COLOR = (80, 80, 80, 80)

# Game States
INIT: str = "INIT"
GREEN_LIGHT: str = "GREEN_LIGHT"
RED_LIGHT: str = "RED_LIGHT"
VICTORY: str = "VICTORY"
GAMEOVER: str = "GAME OVER"
LOADING: str = "LOADING"

START_LINE_PERC = 0.1
FINISH_LINE_PERC = 0.9
GRACE_PERIOD_RED_LIGHT_S = 0.5
MINIMUM_RED_LIGHT_S = 3.0
MINIMUM_GREEN_LIGHT_S = 2.0

# Various
ROOT = os.path.dirname(__file__)
ESP32_IP = "192.168.45.90"
