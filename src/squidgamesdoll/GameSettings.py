import pygame
import yaml


class GameSettings:
    def __init__(self):
        self.areas = {}
        self.settings = {}
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
            settings.settings = config_data.get("settings", {})
            settings.reference_frame = config_data.get("reference_frame", [0, 0])
            print(f"Configuration loaded from {path}")
            return settings
        except FileNotFoundError:
            print(f"Configuration file {path} not found.")
            return
        except yaml.YAMLError as e:
            print(f"Error loading YAML file: {e}")
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
            "settings": self.settings,
            "reference_frame": self.reference_frame,
        }
        try:
            with open(path, "w") as file:
                yaml.dump(config_data, file, default_flow_style=False)
            print(f"Configuration saved to {path}")
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
