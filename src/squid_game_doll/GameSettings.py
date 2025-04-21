import pygame
import yaml
from loguru import logger


class GameSettings:
    def __init__(self):
        self.areas = {}
        self.params = {}
        self.reference_frame = [0, 0]

    def get_reference_frame(self) -> pygame.Rect:
        """
        Get the reference frame defined in the settings.
        """
        return pygame.Rect(0, 0, self.reference_frame[0], self.reference_frame[1])

    @staticmethod
    def load_settings(path: str):
        """
        Load settings from a JSON file.
        """
        settings = GameSettings()

        try:
            with open(path, "r") as file:
                config_data = yaml.safe_load(file)

            settings.areas = {
                key: [GameSettings.list_to_rect(lst) for lst in rects]
                for key, rects in config_data.get("areas", {}).items()
            }
            settings.params = config_data.get("params", {})
            settings.reference_frame = config_data.get("reference_frame", [0, 0])
            logger.info(f"Configuration loaded from {path}")
            return settings
        except FileNotFoundError:
            logger.warning(f"Configuration file {path} not found.")
            return None
        except yaml.YAMLError as e:
            logger.error(f"Error loading YAML file: {e}")
            return None

    @staticmethod
    def rect_to_list(rect):
        return [rect.x, rect.y, rect.w, rect.h]

    @staticmethod
    def list_to_rect(lst):
        return pygame.Rect(*lst)

    def save(self, path: str) -> bool:
        """Save the configuration to a YAML file."""
        config_data = {
            "areas": {key: [self.rect_to_list(r) for r in rects] for key, rects in self.areas.items()},
            "params": self.params,
            "reference_frame": self.reference_frame,
        }
        try:
            with open(path, "w") as file:
                yaml.dump(config_data, file, default_flow_style=False)
            logger.info(f"Configuration saved to {path}")
            return True
        except Exception as e:
            logger.exception("Error saving configuration")
            return False

    @staticmethod
    def default_params() -> dict:
        settings_config = [
            {"key": "exposure", "caption": "Webcam exposure Level", "min": 0, "max": 10, "type": int, "default": 8},
            {
                "key": "yolo_confidence",
                "caption": "YOLO Confidence Level (%)",
                "min": 0,
                "max": 100,
                "type": int,
                "default": 40,
            },
            {
                "key": "bytetrack_confidence",
                "caption": "Bytetrack Confidence Level (%)",
                "min": 0,
                "max": 100,
                "type": int,
                "default": 40,
            },
            {
                "key": "tracking_memory",
                "caption": "ByteTrack frame memory",
                "min": 1,
                "max": 60,
                "type": int,
                "default": 30,
            },
            {
                "key": "pixel_tolerance",
                "caption": "Movement threshold (pixels)",
                "min": 2,
                "max": 50,
                "type": int,
                "default": 15,
            },
            {
                "key": "img_normalization",
                "caption": "Histogram normalization",
                "min": 0,
                "max": 1,
                "type": int,
                "default": 0,
            },
            {
                "key": "img_brightness",
                "caption": "Brightness adjustment",
                "min": 0,
                "max": 1,
                "type": int,
                "default": 0,
            },
            # Add additional configurable settings here.
        ]
        return settings_config

    @staticmethod
    def default_areas(cam_width: int, cam_height: int) -> dict:
        from constants import START_LINE_PERC, FINISH_LINE_PERC

        return {
            "vision": [pygame.Rect(0, 0, cam_width, cam_height)],
            # Start area: top 10%
            "start": [pygame.Rect(0, 0, cam_width, int(START_LINE_PERC * cam_height))],
            # Finish area: bottom 10%
            "finish": [
                pygame.Rect(
                    0,
                    int(FINISH_LINE_PERC * cam_height),
                    cam_width,
                    int((1 - FINISH_LINE_PERC) * cam_height),
                )
            ],
        }
