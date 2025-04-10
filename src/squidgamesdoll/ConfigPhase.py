import pygame
import cv2
import sys
import time
from GameCamera import GameCamera
from constants import FINISH_LINE_PERC, PINK, START_LINE_PERC


class GameConfigPhase:
    def __init__(self, camera: GameCamera, screen_width: int = 1900, screen_height: int = 1200):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        # Center the webcam feed on the screen
        w, h = GameCamera.get_native_resolution(camera.index)
        self.webcam_rect = pygame.Rect((screen_width - w) // 2, (screen_height - h) // 2, w, h)
        pygame.display.set_caption("Game Configuration Phase")

        # Camera instance (expects a GameCamera instance)
        self.camera = camera

        # Define default areas using pygame.Rect:
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
        self.settings = {opt["key"]: opt["default"] for opt in self.settings_config}

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
            {"label": "Vision Area", "mode": "vision", "rect": pygame.Rect(10, 10, 170, 30)},
            {"label": "Start Area", "mode": "start", "rect": pygame.Rect(10, 50, 170, 30)},
            {"label": "Finish Area", "mode": "finish", "rect": pygame.Rect(10, 90, 170, 30)},
            {"label": "Settings", "mode": "settings", "rect": pygame.Rect(10, 130, 170, 30)},
            {"label": "Exit without saving", "mode": "dont_save", "rect": pygame.Rect(10, 170, 170, 30)},
            {"label": "Exit saving changes", "mode": "save", "rect": pygame.Rect(10, 210, 170, 30)},
        ]
        # Define reset icon (for simplicity, a small rect button near the area label)
        self.reset_buttons = {
            "vision": pygame.Rect(screen_width - 130, 10, 120, 30),
            "start": pygame.Rect(screen_width - 130, 50, 120, 30),
            "finish": pygame.Rect(screen_width - 130, 90, 120, 30),
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

    def draw_ui(self, webcam_surf):

        self.screen.fill(PINK)

        # Draw the webcam feed
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
            screen_rect.topleft = (self.webcam_rect.x + self.current_rect.x, self.webcam_rect.y + self.current_rect.y)
            pygame.draw.rect(self.screen, (255, 0, 0), screen_rect, 2)

        # Draw lateral buttons
        for button in self.buttons:
            color = (200, 200, 200) if self.current_mode != button["mode"] else (100, 200, 100)
            pygame.draw.rect(self.screen, color, button["rect"])
            text_surf = self.font.render(button["label"], True, (0, 0, 0))
            self.screen.blit(text_surf, (button["rect"].x + 5, button["rect"].y + 5))

        # Draw reset icons for area modes
        if self.current_mode in self.reset_buttons:
            reset_rect = self.reset_buttons[self.current_mode]
            pygame.draw.rect(self.screen, (255, 100, 100), reset_rect)
            text_surf = self.font.render("Reset", True, (0, 0, 0))
            self.screen.blit(text_surf, (reset_rect.x + 10, reset_rect.y + 5))

        # --- NEW: Draw settings UI with + and - buttons if in settings mode ---
        if self.current_mode == "settings":
            y_offset = 10
            self.settings_buttons = {}  # Dictionary to store plus/minus button rects for each setting
            for opt in self.settings_config:
                key = opt["key"]
                caption = f"{opt['caption']}: {self.settings[key]}"
                text_surf = self.font.render(caption, True, (255, 255, 255))
                x_pos = self.screen_width - 350
                self.screen.blit(text_surf, (x_pos, y_offset))

                # Define plus and minus button rectangles
                minus_rect = pygame.Rect(x_pos + 300, y_offset, 20, 20)
                plus_rect = pygame.Rect(x_pos + 330, y_offset, 20, 20)
                pygame.draw.rect(self.screen, (180, 180, 180), minus_rect)
                pygame.draw.rect(self.screen, (180, 180, 180), plus_rect)
                # Render the '-' and '+' labels
                minus_label = self.font.render("-", True, (0, 0, 0))
                plus_label = self.font.render("+", True, (0, 0, 0))
                self.screen.blit(minus_label, (minus_rect.x + 5, minus_rect.y))
                self.screen.blit(plus_label, (plus_rect.x + 3, plus_rect.y))

                # Store the button rects for event handling
                self.settings_buttons[key] = {"minus": minus_rect, "plus": plus_rect}

                y_offset += 30

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
            self.draw_ui(webcam_surf)

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
            # Return configuration for integration with the rest of your code.
            return self.areas, self.settings

        return None, None


# Example usage:
if __name__ == "__main__":
    import ctypes, os

    ctypes.windll.user32.SetProcessDPIAware()

    # Disable hardware acceleration for webcam on Windows
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

    # Initialize pygame and set up display
    pygame.init()

    cam = GameCamera()
    config_phase = GameConfigPhase(camera=cam, screen_width=1500, screen_height=1200)
    areas, settings = config_phase.run()
    # Now areas and settings are available for further processing.
    print("Configuration completed.", areas, settings)
    pygame.quit()
