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
PLAYER_SIZE: int = 200
FADE_COLOR = (80, 80, 80, 80)

# Game States
INIT: str = "INIT"
GREEN_LIGHT: str = "GREEN_LIGHT"
RED_LIGHT: str = "RED_LIGHT"
VICTORY: str = "VICTORY"
GAMEOVER: str = "GAME OVER"
CONFIG: str = "CONFIG"

FINISH_LINE_PERC = 0.9

# Various
ROOT = os.path.dirname(__file__)
ESP32_IP = "192.168.45.90"
