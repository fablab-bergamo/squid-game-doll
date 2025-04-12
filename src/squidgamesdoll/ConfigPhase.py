import pygame
import cv2
import sys
import time
import yaml
from GameCamera import GameCamera
from constants import FINISH_LINE_PERC, PINK, START_LINE_PERC
from BasePlayerTracker import BasePlayerTracker
from PlayerTrackerUL import PlayerTrackerUL


class GameConfigPhase:
    def __init__(
        self,
        screen: pygame.Surface,
        camera: GameCamera,
        neural_net: BasePlayerTracker,
        config_file: str = "config.yaml",
    ):
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        self.screen = screen
        self.config_file = config_file

        # Center the webcam feed on the screen
        w, h = GameCamera.get_native_resolution(camera.index)
        self.webcam_rect = pygame.Rect((self.screen_width - w) // 2, (self.screen_height - h) // 2, w, h)
        pygame.display.set_caption("Game Configuration Phase")

        # Camera instance (expects a GameCamera instance)
        self.camera = camera

        # Neural network instance (expects a BasePlayerTracker instance)
        self.neural_net = neural_net

        self.settings = {}
        self.areas = {}

        if not self.load_from_yaml():
            self.__setup_defaults()

        # Configurable settings: list of dicts (min, max, key, caption, type, default)
        self.settings_config = [
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
            # Add additional configurable settings here.
        ]
        # Create a dictionary to hold current setting values.
        for opt in self.settings_config:
            if self.settings.get(opt["key"]) is None:
                print(f"Warning: {opt['key']} not found in config file. Using default value.")
                self.settings = {opt["key"]: opt["default"] for opt in self.settings_config}

        self.settings_buttons = {}

        # UI state
        self.current_mode = "vision"  # Can be "vision", "start", "finish", "settings"
        self.font = pygame.font.SysFont("Arial", 16)
        self.clock = pygame.time.Clock()

        # For drawing rectangles
        self.drawing = False
        self.start_pos = None
        self.current_rect = None
        self.last_click_time = 0  # For detecting double clicks

        # Define lateral button areas (simple list of buttons)
        self.buttons = [
            {"label": "Vision Area", "mode": "vision"},
            {"label": "Start Area", "mode": "start"},
            {"label": "Finish Area", "mode": "finish"},
            {"label": "Settings", "mode": "settings"},
            {"label": "Neural net preview", "mode": "nn_preview"},
            {"label": "Exit without saving", "mode": "dont_save"},
            {"label": "Exit saving changes", "mode": "save"},
        ]

        # Compute buttons positions
        for idx, button in enumerate(self.buttons):
            button["rect"] = pygame.Rect(10, 10 + idx * 40, 170, 30)

        # Define reset icon (for simplicity, a small rect button near the area label)
        self.reset_buttons = {
            "vision": pygame.Rect(self.screen_width - 130, 10, 120, 30),
            "start": pygame.Rect(self.screen_width - 130, 50, 120, 30),
            "finish": pygame.Rect(self.screen_width - 130, 90, 120, 30),
        }

    def __setup_defaults(self):
        # Vision area: full screen.
        self.areas = {
            "vision": [pygame.Rect(0, 0, self.webcam_rect.width, self.webcam_rect.height)],
            # Start area: top 10%
            "start": [pygame.Rect(0, 0, self.webcam_rect.width, int(START_LINE_PERC * self.webcam_rect.height))],
            # Finish area: bottom 10%
            "finish": [
                pygame.Rect(
                    0,
                    int(FINISH_LINE_PERC * self.webcam_rect.height),
                    self.webcam_rect.width,
                    int((1 - FINISH_LINE_PERC) * self.webcam_rect.height),
                )
            ],
        }

    def convert_cv2_to_pygame(self, cv_image):
        """Convert an OpenCV image to a pygame surface."""
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        cv_image = cv2.transpose(cv_image)  # transpose to match pygame orientation if needed
        surface = pygame.surfarray.make_surface(cv_image)
        surface = pygame.transform.flip(surface, True, False)
        return surface

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Check for lateral button clicks (unchanged)
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                for button in self.buttons:
                    if button["rect"].collidepoint(pos):
                        self.current_mode = button["mode"]
                        print(f"Switched to mode: {self.current_mode}")
                        self.drawing = False
                        self.current_rect = None
                        return

                if self.current_mode in self.reset_buttons:
                    if self.reset_buttons[self.current_mode].collidepoint(pos):
                        self.reset_area(self.current_mode)
                        print(f"Reset {self.current_mode} area to default.")
                        return

                now = time.time()
                if now - self.last_click_time < 0.3 and self.current_mode != "settings":
                    rects = self.areas[self.current_mode].copy()
                    rects.reverse()  # Check from the last rectangle to the first
                    for rect in rects:
                        # Adjust rectangle position to screen coordinates for collision check
                        screen_rect = rect.copy()
                        screen_rect.x += self.webcam_rect.x
                        screen_rect.y += self.webcam_rect.y
                        if screen_rect.collidepoint(pos):
                            self.areas[self.current_mode].remove(rect)
                            print(f"Removed rectangle {rect} from {self.current_mode}.")
                            return
                self.last_click_time = now

                # Handle settings adjustments (unchanged)
                if self.current_mode == "settings":
                    # The settings buttons are handled later below.
                    pass
                # For area modes, start drawing a new rectangle.
                elif self.current_mode != "settings":
                    self.drawing = True
                    # Convert global mouse position to feed-relative coordinates.
                    self.start_pos = (pos[0] - self.webcam_rect.x, pos[1] - self.webcam_rect.y)

            if event.type == pygame.MOUSEMOTION:
                if self.drawing and self.current_mode != "settings":
                    # Convert current position to feed-relative coordinates.
                    current_pos = (event.pos[0] - self.webcam_rect.x, event.pos[1] - self.webcam_rect.y)
                    x = min(self.start_pos[0], current_pos[0])
                    y = min(self.start_pos[1], current_pos[1])
                    width = abs(self.start_pos[0] - current_pos[0])
                    height = abs(self.start_pos[1] - current_pos[1])

                    # Make sure X,Y coordinates are within the webcam feed.
                    x = max(0, min(x, self.webcam_rect.width))
                    y = max(0, min(y, self.webcam_rect.height))
                    width = max(0, min(width, self.webcam_rect.width - x))
                    height = max(0, min(height, self.webcam_rect.height - y))

                    self.current_rect = pygame.Rect(x, y, width, height)

            if event.type == pygame.MOUSEBUTTONUP:
                if self.drawing and self.current_mode != "settings":
                    if self.current_rect and self.current_rect.width > 0 and self.current_rect.height > 0:
                        self.areas[self.current_mode].append(self.current_rect)
                        print(f"Added rectangle {self.current_rect} to {self.current_mode}.")
                        self.areas[self.current_mode] = self.minimize_rectangles(self.areas[self.current_mode])

                    self.drawing = False
                    self.current_rect = None

            # Handle settings adjustment via + and - buttons (unchanged)
            if event.type == pygame.MOUSEBUTTONDOWN and self.current_mode == "settings":
                pos = event.pos
                for opt in self.settings_config:
                    key = opt["key"]
                    if key in self.settings_buttons:
                        buttons = self.settings_buttons[key]
                        if buttons["minus"].collidepoint(pos):
                            new_val = self.settings[key] - 1
                            if new_val >= opt["min"]:
                                self.settings[key] = new_val
                                print(f"{key} decreased to {self.settings[key]}")
                            else:
                                print(f"{key} is at minimum value.")
                        elif buttons["plus"].collidepoint(pos):
                            new_val = self.settings[key] + 1
                            if new_val <= opt["max"]:
                                self.settings[key] = new_val
                                print(f"{key} increased to {self.settings[key]}")
                            else:
                                print(f"{key} is at maximum value.")

            # TODO: Add joystick events handling here if needed.

    def reset_area(self, area_name):
        """Reset the rectangles for a given area to their default value relative to the webcam feed."""
        if area_name == "vision":
            self.areas["vision"] = [pygame.Rect(0, 0, self.webcam_rect.width, self.webcam_rect.height)]
        elif area_name == "start":
            self.areas["start"] = [pygame.Rect(0, 0, self.webcam_rect.width, int(0.1 * self.webcam_rect.height))]
        elif area_name == "finish":
            self.areas["finish"] = [
                pygame.Rect(
                    0, int(0.9 * self.webcam_rect.height), self.webcam_rect.width, int(0.1 * self.webcam_rect.height)
                )
            ]

    def validate_configuration(self):
        """
        Check if the configuration is valid.
        Returns a list of warning messages if there is no intersection between:
         - any rectangle in the starting area and any rectangle in the vision area, or
         - any rectangle in the finish area and any rectangle in the vision area.
        """
        warnings = []
        # Validate start area intersection with vision area.
        valid_start = any(
            r_start.colliderect(r_vision)
            for r_start in self.areas.get("start", [])
            for r_vision in self.areas.get("vision", [])
        )
        if not valid_start:
            warnings.append("Start area does not intersect with vision area!")

        # Validate finish area intersection with vision area.
        valid_finish = any(
            r_finish.colliderect(r_vision)
            for r_finish in self.areas.get("finish", [])
            for r_vision in self.areas.get("vision", [])
        )
        if not valid_finish:
            warnings.append("Finish area does not intersect with vision area!")

        return warnings

    def minimize_rectangles(self, rect_list):
        """
        Given a list of pygame.Rect objects, returns a new list with rectangles
        that are not completely contained within another rectangle in the list.
        This minimizes redundancy by removing included (nested) rectangles.
        """
        minimal = []
        for rect in rect_list:
            is_included = False
            for other in rect_list:
                if rect is not other and other.contains(rect):
                    is_included = True
                    break
            if not is_included:
                minimal.append(rect)
        return minimal

    def bounding_rectangle(self, rect_list):
        """
        Compute and return a pygame.Rect that is the bounding rectangle covering
        all rectangles in rect_list. If rect_list is empty, return None.
        """
        if not rect_list:
            return None
        x_min = min(rect.left for rect in rect_list)
        y_min = min(rect.top for rect in rect_list)
        x_max = max(rect.right for rect in rect_list)
        y_max = max(rect.bottom for rect in rect_list)
        return pygame.Rect(x_min, y_min, x_max - x_min, y_max - y_min)

    def draw_buttons(self, surface: pygame.Surface):
        # Draw lateral buttons
        for button in self.buttons:
            is_selected = self.current_mode == button["mode"]

            color = (100, 200, 100) if is_selected else (200, 200, 200)
            pygame.draw.rect(surface, color, button["rect"])

            # Add border around selected button
            if is_selected:
                pygame.draw.rect(surface, (255, 255, 0), button["rect"], 2)

            text_surf = self.font.render(button["label"], True, (0, 0, 0))
            surface.blit(text_surf, (button["rect"].x + 5, button["rect"].y + 5))

        # Draw reset icons for area modes
        if self.current_mode in self.reset_buttons:
            reset_rect = self.reset_buttons[self.current_mode]
            pygame.draw.rect(surface, (255, 100, 100), reset_rect)
            text_surf = self.font.render("Reset", True, (0, 0, 0))
            surface.blit(text_surf, (reset_rect.x + 10, reset_rect.y + 5))

    def draw_settings(self, surface: pygame.Surface):
        y_offset = 10
        self.settings_buttons = {}  # Dictionary to store plus/minus button rects for each setting
        for opt in self.settings_config:
            key = opt["key"]
            caption = f"{opt['caption']}: {self.settings[key]}"
            text_surf = self.font.render(caption, True, (255, 255, 255))
            x_pos = surface.get_width() - 350
            surface.blit(text_surf, (x_pos, y_offset))

            # Define plus and minus button rectangles
            minus_rect = pygame.Rect(x_pos + 300, y_offset, 20, 20)
            plus_rect = pygame.Rect(x_pos + 330, y_offset, 20, 20)
            pygame.draw.rect(surface, (180, 180, 180), minus_rect)
            pygame.draw.rect(surface, (180, 180, 180), plus_rect)
            # Render the '-' and '+' labels
            minus_label = self.font.render("-", True, (0, 0, 0))
            plus_label = self.font.render("+", True, (0, 0, 0))
            surface.blit(minus_label, (minus_rect.x + 5, minus_rect.y))
            surface.blit(plus_label, (plus_rect.x + 3, plus_rect.y))

            # Store the button rects for event handling
            self.settings_buttons[key] = {"minus": minus_rect, "plus": plus_rect}
            y_offset += 30

    def apply_vision_frame(
        self, rectangles: list[pygame.Rect], webcam_surface: pygame.Surface, frame: cv2.UMat
    ) -> cv2.UMat:
        # Get the bounding rectangle of the vision area
        bounding_rect = self.bounding_rectangle(rectangles)
        if bounding_rect:
            # We need to zero frame areas outside the list of rectangles in vision_area
            # Let's create a mask for the vision area
            mask = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mask[:] = 0  # Initialize mask to zero
            for rect in rectangles:
                # Convert rect coordinates to frame coordinates
                x = int(rect.x / webcam_surface.get_width() * frame.shape[1])
                y = int(rect.y / webcam_surface.get_height() * frame.shape[0])
                w = int(rect.width / webcam_surface.get_width() * frame.shape[1])
                h = int(rect.height / webcam_surface.get_height() * frame.shape[0])
                # webcam surface is mirrored-flipped, so we need to adjust the x coordinate for cropping correctly
                x = frame.shape[1] - (x + w)  # Adjust x coordinate for mirrored image
                # Draw the rectangle on the mask
                cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

            # Apply the mask to the frame
            frame = cv2.bitwise_and(frame, frame, mask=mask)

            # Compute proportions relative to the webcam Sruf, and then apply to the raw CV2 frame
            x_ratio = bounding_rect.x / webcam_surface.get_width()
            y_ratio = bounding_rect.y / webcam_surface.get_height()
            w_ratio = bounding_rect.width / webcam_surface.get_width()
            h_ratio = bounding_rect.height / webcam_surface.get_height()
            # Apply the bounding rectangle to the webcam surface
            x = int(x_ratio * frame.shape[1])
            y = int(y_ratio * frame.shape[0])
            w = int(w_ratio * frame.shape[1])
            h = int(h_ratio * frame.shape[0])

            # webcam surface is mirrored-flipped, so we need to adjust the x coordinate for cropping correctly
            x = frame.shape[1] - (x + w)  # Adjust x coordinate for mirrored image
            frame = frame[y : y + h, x : x + w]  # Crop the frame to the bounding rectangle

            cv2.imshow("Vision Area", frame)  # Show the cropped frame for debugging
            cv2.waitKey(1)
            return frame
        # Feed the full frame otherwise
        return None

    def draw_ui(self, webcam_surf: pygame.Surface, frame: cv2.UMat):

        self.screen.fill(PINK)

        if self.current_mode == "nn_preview":
            # Apply the vision frame to the webcam surface
            cropped_frame = self.apply_vision_frame(self.settings["vision"], webcam_surf, frame)
            if cropped_frame is not None:
                # Show the frame that will be fed to the neural network, which may apply further processing.
                preview = self.neural_net.get_sample_frame(cropped_frame)
                # Convert the frame to a pygame surface and display it
                nn_surf = self.convert_cv2_to_pygame(preview)
                # Resize keeping the aspect ratio
                aspect_ratio = nn_surf.get_width() / nn_surf.get_height()
                if nn_surf.get_width() > nn_surf.get_height():
                    new_width = int(self.screen_width * 0.8)
                    new_height = int(new_width / aspect_ratio)
                else:
                    new_height = int(self.screen_height * 0.8)
                    new_width = int(new_height * aspect_ratio)
                nn_surf_resized = pygame.transform.scale(nn_surf, (new_width, new_height))
                # Center the resized surface
                x_offset = (self.screen_width - new_width) // 2
                y_offset = (self.screen_height - new_height) // 2
                self.screen.blit(nn_surf_resized, (x_offset, y_offset))
                # Draw a rectangle around the neural net preview
                pygame.draw.rect(self.screen, (255, 255, 0), (x_offset, y_offset, new_width, new_height), 2)
                # Add a label
                label_surf = self.font.render(
                    f"Neural Network Preview ({nn_surf.get_width()} x {nn_surf.get_height()})", True, (255, 255, 255)
                )
                label_rect = label_surf.get_rect(center=(x_offset + new_width // 2, y_offset - 20))
                self.screen.blit(label_surf, label_rect.topleft)
        else:
            # Draw the webcam feed in normal modes
            self.screen.blit(webcam_surf, self.webcam_rect.topleft)

            # --- NEW: Draw all configured areas with filled, transparent colors ---
            area_colors = {
                "vision": (0, 255, 0, 100),  # green
                "start": (0, 0, 255, 100),  # blue
                "finish": (255, 0, 0, 100),  # red
            }
            for area_name, rect_list in self.areas.items():
                # Create a transparent overlay surface
                overlay = pygame.Surface((self.webcam_rect.width, self.webcam_rect.height), pygame.SRCALPHA)
                color = area_colors.get(area_name, (200, 200, 200, 100))
                for rect in rect_list:
                    pygame.draw.rect(overlay, color, rect)
                    color_outline = (color[0], color[1], color[2], 255)  # Opaque outline color
                    pygame.draw.rect(overlay, color_outline, rect, 1)  # Draw outline
                self.screen.blit(overlay, self.webcam_rect.topleft)

            # Represent the bouding rectangle of active mode with dashed lines
            for area_name, rect_list in self.areas.items():
                if self.current_mode == area_name:
                    bounding_rect = self.bounding_rectangle(rect_list)
                    if bounding_rect:
                        pygame.draw.rect(overlay, (255, 255, 0), bounding_rect, 2)

            # Blit the overlay on top of the webcam feed
            self.screen.blit(overlay, self.webcam_rect.topleft)

            # Draw the rectangle currently being drawn (if any) as an outline
            if self.drawing and self.current_rect:
                screen_rect = self.current_rect.copy()
                screen_rect.topleft = (
                    self.webcam_rect.x + self.current_rect.x,
                    self.webcam_rect.y + self.current_rect.y,
                )
                pygame.draw.rect(self.screen, (255, 0, 0), screen_rect, 2)

        self.draw_buttons(self.screen)

        if self.current_mode == "settings":
            self.draw_settings(self.screen)

        # Validate configuration and display warning messages if needed.
        warnings = self.validate_configuration()
        if warnings:
            y_warning = self.screen_height - (20 * len(warnings)) - 10
            for warning in warnings:
                warning_surf = self.font.render(warning, True, (0, 0, 0))
                self.screen.blit(warning_surf, (self.webcam_rect.x, y_warning))
                y_warning += 20

    def run(self):
        """Main loop for the configuration phase."""
        running = True
        while running:
            self.handle_events()

            # Read from the camera
            ret, frame = self.camera.read()
            if not ret:
                print("Failed to read from camera.")
                continue

            # Convert cv2 frame to a pygame surface.
            webcam_surf = self.convert_cv2_to_pygame(frame)

            # Draw all UI components
            self.draw_ui(webcam_surf, frame)

            # Update the display
            pygame.display.flip()
            self.clock.tick(30)  # limit to 30 fps

            # For demonstration, exit when the user presses ESC
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE] or self.current_mode == "dont_save" or self.current_mode == "save":
                running = False

        if self.current_mode == "save":
            # After quitting, configuration data is available:
            print("Final area definitions:", self.areas)
            print("Final settings:", self.settings)
            self.save_to_yaml()
            # Return configuration for integration with the rest of your code.
            return self.areas, self.settings

        return None, None

    def rect_to_list(self, rect):
        return [rect.x, rect.y, rect.w, rect.h]

    def list_to_rect(self, lst):
        return pygame.Rect(*lst)

    def save_to_yaml(self) -> bool:
        """Save the configuration to a YAML file."""
        config_data = {
            "areas": {key: [self.rect_to_list(r) for r in rects] for key, rects in self.areas.items()},
            "settings": self.settings,
        }
        try:
            with open(self.config_file, "w") as file:
                yaml.dump(config_data, file, default_flow_style=False)
            print(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

    def load_from_yaml(self) -> bool:
        """Load the configuration from a YAML file."""
        try:
            with open(self.config_file, "r") as file:
                config_data = yaml.safe_load(file)

            self.areas = {
                key: [self.list_to_rect(lst) for lst in rects] for key, rects in config_data.get("areas", {}).items()
            }
            self.settings = config_data.get("settings", {})
            print(f"Configuration loaded from {self.config_file}")
            return True
        except FileNotFoundError:
            print(f"Configuration file {self.config_file} not found.")
            return False
        except yaml.YAMLError as e:
            print(f"Error loading YAML file: {e}")
            return False


# Example usage:
if __name__ == "__main__":
    import ctypes, os

    ctypes.windll.user32.SetProcessDPIAware()

    # Disable hardware acceleration for webcam on Windows
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

    # Initialize pygame and set up display
    pygame.init()
    screen = pygame.display.set_mode((1500, 1200))
    cam = GameCamera()
    nn = PlayerTrackerUL()
    config_phase = GameConfigPhase(camera=cam, screen=screen, neural_net=nn)
    areas, settings = config_phase.run()
    # Now areas and settings are available for further processing.
    print("Configuration completed.", areas, settings)
    pygame.quit()
