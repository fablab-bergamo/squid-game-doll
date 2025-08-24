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

    def get_param(self, key: str, default_value=None):
        """
        Get a parameter value from the settings.
        """
        if type(self.params) is dict:
            return self.params.get(key, default_value)
        for param in self.params:
            if param["key"] == key:
                return param["value"]
        return default_value

    def get_gameplay_areas(self):
        """
        Get areas transformed from setup coordinates to gameplay coordinates.
        
        Setup coordinates are saved as drawn on horizontally flipped display.
        Gameplay coordinates need to be transformed to work with the camera frame.
        
        Transform: x_gameplay = frame_width - (x_setup + width_setup)
        
        Returns:
            dict: Areas with coordinates transformed for gameplay
        """
        if not hasattr(self, '_gameplay_areas_cache'):
            self._gameplay_areas_cache = {}
            frame_width = self.reference_frame[0]
            
            for area_name, rect_list in self.areas.items():
                gameplay_rects = []
                for rect in rect_list:
                    # Transform x-coordinate from setup space to gameplay space
                    gameplay_x = frame_width - (rect.x + rect.width)
                    # Y-coordinate and dimensions remain the same
                    gameplay_rect = pygame.Rect(gameplay_x, rect.y, rect.width, rect.height)
                    gameplay_rects.append(gameplay_rect)
                self._gameplay_areas_cache[area_name] = gameplay_rects
        
        return self._gameplay_areas_cache
    
    def invalidate_gameplay_cache(self):
        """Invalidate the gameplay areas cache when areas are modified."""
        if hasattr(self, '_gameplay_areas_cache'):
            delattr(self, '_gameplay_areas_cache')

    @staticmethod
    def load_settings(path: str):
        """
        Load settings from a JSON file.
        """
        settings = GameSettings()

        try:
            with open(path, "r") as file:
                config_data = yaml.load(file, Loader=yaml.FullLoader)

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
        # Invalidate gameplay cache when saving (areas may have changed)
        self.invalidate_gameplay_cache()
        
        config_data = {
            "areas": {key: [self.rect_to_list(r) for r in rects] for key, rects in self.areas.items()},
            "params": self.params,
            "reference_frame": self.reference_frame,
        }
        try:
            with open(path, "w") as file:
                yaml.dump(
                    config_data,
                    file,
                    default_flow_style=False,
                    Dumper=yaml.Dumper,
                )
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
                "value": 40,
            },
            {
                "key": "bytetrack_confidence",
                "caption": "Bytetrack Confidence Level (%)",
                "min": 0,
                "max": 100,
                "type": int,
                "default": 40,
                "value": 40,
            },
            {
                "key": "tracking_memory",
                "caption": "ByteTrack frame memory",
                "min": 1,
                "max": 60,
                "type": int,
                "default": 30,
                "value": 30,
            },
            {
                "key": "pixel_tolerance",
                "caption": "Movement threshold (pixels)",
                "min": 2,
                "max": 50,
                "type": int,
                "default": 15,
                "value": 15,
            },
            {
                "key": "img_normalization",
                "caption": "Histogram normalization",
                "min": 0,
                "max": 1,
                "type": int,
                "default": 0,
                "value": 0,
            },
            {
                "key": "img_brightness",
                "caption": "Brightness adjustment",
                "min": 0,
                "max": 1,
                "type": int,
                "default": 0,
                "value": 0,
            },
            {
                "key": "ttl",
                "caption": "Maximum time for hidden players (seconds)",
                "min": 5,
                "max": 60,
                "type": int,
                "default": 60,
                "value": 60,
            },
            # Add additional configurable settings here.
        ]
        return settings_config

    @staticmethod
    def default_areas(cam_width: int, cam_height: int) -> dict:
        from .constants import START_LINE_PERC, FINISH_LINE_PERC

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
