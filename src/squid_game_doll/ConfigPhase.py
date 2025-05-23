import pygame
import cv2
import sys
import time
from loguru import logger
from .GameCamera import GameCamera
from .constants import PINK
from .BasePlayerTracker import BasePlayerTracker
from .GameSettings import GameSettings


class GameConfigPhase:
    VIDEO_SCREEN_SIZE_PERCENT = 0.8

    def __init__(
        self,
        screen: pygame.Surface,
        camera: GameCamera,
        neural_net: BasePlayerTracker,
        game_settings: GameSettings,
        config_file: str = "config.yaml",
    ):
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        self.screen = screen
        self.game_settings = game_settings
        self.config_file = config_file

        # Center and resize the webcam feed on the screen
        w, h = GameCamera.get_native_resolution(camera.index)
        aspect_ratio = w / h
        new_width = 100
        new_height = 100
        while (
            new_width < self.screen_width * GameConfigPhase.VIDEO_SCREEN_SIZE_PERCENT
            and new_height < self.screen_height * GameConfigPhase.VIDEO_SCREEN_SIZE_PERCENT
        ):
            if aspect_ratio > 1:
                new_width += 100
                new_height = int(h * new_width / w)
            else:
                new_height += 100
                new_width = int(w * new_height / h)

        self.webcam_rect = pygame.Rect(
            (self.screen_width - new_width) // 2, (self.screen_height - new_height) // 2, new_width, new_height
        )
        self.webcam_to_screen_ratio = new_height / h
        self.game_settings.reference_frame = [
            int(self.webcam_rect.width / self.webcam_to_screen_ratio),
            int(self.webcam_rect.height / self.webcam_to_screen_ratio),
        ]
        pygame.display.set_caption("Game Configuration Phase")

        # Camera instance (expects a GameCamera instance)
        self.camera = camera

        # Neural network instance (expects a BasePlayerTracker instance)
        self.neural_net = neural_net

        if len(self.game_settings.areas) == 0:
            self.__setup_defaults()

        # Configurable settings: list of dicts (min, max, key, caption, type, default)
        self.settings_config = GameSettings.default_params()

        # Create a dictionary to hold current setting values.
        for opt in self.settings_config:
            if opt["key"] not in self.game_settings.params:
                logger.warning(f"Warning: {opt['key']} not found in config file. Using default value.")
                self.game_settings.params = {opt["key"]: opt["default"] for opt in self.settings_config}

        self.settings_buttons = {}

        # UI state
        self.current_mode = "vision"  # Can be "vision", "start", "finish", "settings"
        self.font = pygame.font.SysFont("Arial", 16)
        self.big_font = pygame.font.SysFont("Arial", 64)
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
        self.game_settings.areas = GameSettings.default_areas(self.webcam_rect.width, self.webcam_rect.height)

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
                        logger.debug(f"Switched to mode: {self.current_mode}")
                        self.drawing = False
                        self.current_rect = None
                        if self.current_mode == "nn_preview":
                            self.neural_net.reset()
                        return

                if self.current_mode in self.reset_buttons:
                    if self.reset_buttons[self.current_mode].collidepoint(pos):
                        self.reset_area(self.current_mode)
                        logger.info(f"Reset {self.current_mode} area to default.")
                        return

                now = time.time()
                if now - self.last_click_time < 0.3 and self.current_mode != "settings":
                    rects = self.game_settings.areas[self.current_mode].copy()
                    rects.reverse()  # Check from the last rectangle to the first
                    for rect in rects:
                        # Adjust rectangle position to screen coordinates for collision check
                        saved_rec = GameConfigPhase.scale_rect(rect, self.webcam_to_screen_ratio)
                        saved_rec.topleft = (self.webcam_rect.x + saved_rec.x, self.webcam_rect.y + saved_rec.y)
                        if saved_rec.collidepoint(pos):
                            self.game_settings.areas[self.current_mode].remove(rect)
                            logger.debug(f"Removed rectangle {rect} from {self.current_mode}.")
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

                    self.current_rect = GameConfigPhase.scale_rect(
                        pygame.Rect(x, y, width, height), 1 / self.webcam_to_screen_ratio
                    )

            if event.type == pygame.MOUSEBUTTONUP:
                if self.drawing and self.current_mode != "settings":
                    if self.current_rect and self.current_rect.width > 0 and self.current_rect.height > 0:
                        original_rect = self.current_rect.copy()
                        self.game_settings.areas[self.current_mode].append(original_rect)
                        logger.debug(f"Added rectangle {original_rect} to {self.current_mode}.")
                        self.game_settings.areas[self.current_mode] = self.minimize_rectangles(
                            self.game_settings.areas[self.current_mode]
                        )

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
                            new_val = self.game_settings.params[key] - 1
                            if new_val >= opt["min"]:
                                self.game_settings.params[key] = new_val
                                logger.debug(f"{key} decreased to {self.game_settings.params[key]}")
                            else:
                                logger.debug(f"{key} is at minimum value.")
                        elif buttons["plus"].collidepoint(pos):
                            new_val = self.game_settings.params[key] + 1
                            if new_val <= opt["max"]:
                                self.game_settings.params[key] = new_val
                                logger.debug(f"{key} increased to {self.game_settings.params[key]}")
                            else:
                                logger.debug(f"{key} is at maximum value.")

            # TODO: Add joystick events handling here if needed.

    def reset_area(self, area_name):
        """Reset the rectangles for a given area to their default value relative to the webcam feed."""
        if area_name == "vision":
            self.game_settings.areas["vision"] = [
                GameConfigPhase.scale_rect(
                    pygame.Rect(0, 0, self.webcam_rect.width, self.webcam_rect.height), 1 / self.webcam_to_screen_ratio
                )
            ]
        elif area_name == "start":
            self.game_settings.areas["start"] = [
                GameConfigPhase.scale_rect(
                    pygame.Rect(0, 0, self.webcam_rect.width, int(0.1 * self.webcam_rect.height)),
                    1 / self.webcam_to_screen_ratio,
                )
            ]
        elif area_name == "finish":
            limit = int(0.9 * self.webcam_rect.height)
            self.game_settings.areas["finish"] = [
                GameConfigPhase.scale_rect(
                    pygame.Rect(
                        0,
                        limit,
                        self.webcam_rect.width,
                        self.webcam_rect.height - limit,
                    ),
                    1 / self.webcam_to_screen_ratio,
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
            for r_start in self.game_settings.areas.get("start", [])
            for r_vision in self.game_settings.areas.get("vision", [])
        )
        if not valid_start:
            warnings.append("Start area does not intersect with vision area!")

        # Validate finish area intersection with vision area.
        valid_finish = any(
            r_finish.colliderect(r_vision)
            for r_finish in self.game_settings.areas.get("finish", [])
            for r_vision in self.game_settings.areas.get("vision", [])
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
            caption = f"{opt['caption']}: {self.game_settings.params[key]}"
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

    def draw_ui(self, webcam_surf: pygame.Surface, webcam_frame: cv2.UMat):

        self.screen.fill(PINK)

        if self.current_mode == "nn_preview":
            # Apply the vision frame to the webcam surface
            nn_frame, webcam_frame, rect = self.camera.read_nn(self.game_settings, self.neural_net.get_max_size())

            if nn_frame is not None:
                # Convert the frame to a pygame surface and display it
                nn_surf = self.convert_cv2_to_pygame(nn_frame)
                # Resize keeping the aspect ratio
                aspect_ratio = nn_surf.get_width() / nn_surf.get_height()
                new_width = 100
                new_height = 100
                while (
                    new_width < self.screen_width * GameConfigPhase.VIDEO_SCREEN_SIZE_PERCENT
                    and new_height < self.screen_height * GameConfigPhase.VIDEO_SCREEN_SIZE_PERCENT
                ):
                    if aspect_ratio > 1:
                        new_width += 100
                        new_height = int(nn_surf.get_height() * new_width / nn_surf.get_width())
                    else:
                        new_height += 100
                        new_width = int(nn_surf.get_width() * new_height / nn_surf.get_height())

                logger.debug(
                    f"read_nn: original dimensions {webcam_frame.shape[1]} x {webcam_frame.shape[0]}, Resized dimensions {(nn_frame.shape[1], nn_frame.shape[0])}, rect: {rect}, size on screen {new_width} x {new_height}"
                )
                nn_surf_resized = pygame.transform.scale(nn_surf, (new_width, new_height))
                # Center the resized surface
                x_offset = (self.screen_width - new_width) // 2
                y_offset = (self.screen_height - new_height) // 2

                # Run the model and highlight detections
                for p in self.neural_net.process_nn_frame(nn_frame, self.game_settings):
                    if p is not None:
                        bbox = p.get_bbox()
                        # Now apply scaling factors from NN Frame to webcam frame AND from webcam frame to resized surface
                        x = int(bbox[0] * new_width / rect.width * rect.width / nn_frame.shape[1])
                        y = int(bbox[1] * new_height / rect.height * rect.height / nn_frame.shape[0])
                        w = int(bbox[2] * new_width / rect.width * rect.width / nn_frame.shape[1])
                        h = int(bbox[3] * new_height / rect.height * rect.height / nn_frame.shape[0])
                        # Flip the x coordinate to match pygame orientation
                        x = new_width - x - w
                        logger.debug(f"Player ID: {p.get_id()} bbox: {bbox} scaled:{(x, y, w, h)}")

                        # Draw the bounding box around the detected player
                        pygame.draw.rect(nn_surf_resized, (128, 255, 255), (x, y, w, h), 5)
                        # Draw the player ID
                        id_surf = self.big_font.render(str(p.get_id()), True, (255, 0, 0))
                        nn_surf_resized.blit(id_surf, (x + 5, y + 5))

                self.screen.blit(nn_surf_resized, (x_offset, y_offset))

                # Draw a rectangle around the neural net preview
                pygame.draw.rect(self.screen, (255, 255, 0), (x_offset, y_offset, new_width, new_height), 2)
                # Add a label
                label_surf = self.font.render(
                    f"Neural Network Preview ({nn_surf.get_width()} x {nn_surf.get_height()}, FPS: {self.neural_net.get_fps()})",
                    True,
                    (255, 255, 255),
                )
                label_rect = label_surf.get_rect(center=(x_offset + new_width // 2, y_offset - 20))
                self.screen.blit(label_surf, label_rect.topleft)
        else:
            # Resize the webcam surface to fit the screen
            webcam_surf = pygame.transform.scale(webcam_surf, (self.webcam_rect.w, self.webcam_rect.h))

            # Draw the webcam feed in normal modes
            self.screen.blit(webcam_surf, self.webcam_rect.topleft)

            # --- NEW: Draw all configured areas with filled, transparent colors ---
            area_colors = {
                "vision": (0, 255, 0, 100),  # green
                "start": (0, 0, 255, 100),  # blue
                "finish": (255, 0, 0, 100),  # red
            }
            for area_name, rect_list in sorted(self.game_settings.areas.items(), reverse=True):
                # Create a transparent overlay surface
                overlay = pygame.Surface((self.webcam_rect.width, self.webcam_rect.height), pygame.SRCALPHA)
                color = area_colors.get(area_name, (200, 200, 200, 100))
                for rect in GameConfigPhase.scale(rect_list, self.webcam_to_screen_ratio):
                    pygame.draw.rect(overlay, color, rect)
                    color_outline = (color[0], color[1], color[2], 255)  # Opaque outline color
                    pygame.draw.rect(overlay, color_outline, rect, 1)  # Draw outline
                self.screen.blit(overlay, self.webcam_rect.topleft)

            # Represent the bouding rectangle of active mode with dashed lines
            for area_name, rect_list in self.game_settings.areas.items():
                if self.current_mode == area_name:
                    bounding_rect = self.bounding_rectangle(
                        GameConfigPhase.scale(rect_list, self.webcam_to_screen_ratio)
                    )
                    if bounding_rect:
                        pygame.draw.rect(overlay, (255, 255, 0), bounding_rect, 2)

            # Blit the overlay on top of the webcam feed
            self.screen.blit(overlay, self.webcam_rect.topleft)

            # Draw the rectangle currently being drawn (if any) as an outline
            if self.drawing and self.current_rect:
                screen_rect = GameConfigPhase.scale_rect(self.current_rect, self.webcam_to_screen_ratio)
                screen_rect.topleft = (
                    self.webcam_rect.x + screen_rect.x,
                    self.webcam_rect.y + screen_rect.y,
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

    def run(self) -> GameSettings | None:
        """Main loop for the configuration phase."""
        running = True
        while running:
            self.handle_events()

            # Read from the camera
            ret, frame = self.camera.read()
            if not ret:
                logger.error("Failed to read from camera.")
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
            self.game_settings.reference_frame = [
                int(self.webcam_rect.width / self.webcam_to_screen_ratio),
                int(self.webcam_rect.height / self.webcam_to_screen_ratio),
            ]
            self.game_settings.save(self.config_file)
            return self.game_settings

        return None

    @staticmethod
    def scale(rect_list: list[pygame.Rect], scale_factor: float) -> list:
        """
        Scale a list of pygame.Rect objects by a given scale factor.
        """
        return [
            pygame.Rect(
                round(rect.x * scale_factor, 0),
                round(rect.y * scale_factor, 0),
                round(rect.width * scale_factor, 0),
                round(rect.height * scale_factor, 0),
            )
            for rect in rect_list
        ]

    @staticmethod
    def scale_rect(rect: pygame.Rect, scale_factor: float) -> list:
        return GameConfigPhase.scale([rect], scale_factor)[0]
