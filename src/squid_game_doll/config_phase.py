import pygame
import cv2
import sys
import time
from loguru import logger
from .game_camera import GameCamera
from .constants import PINK
from .base_player_tracker import BasePlayerTracker
from .game_settings import GameSettings
from .face_extractor import FaceExtractor
from .cuda_utils import cuda_cvt_color
from .laser_finder_nn import LaserFinderNN
from .laser_shooter import LaserShooter


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
        w, h = camera.get_native_resolution(camera.index)
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

        # Face extractor for testing face detection
        self.face_extractor = FaceExtractor()
        self.current_faces = []  # List to store currently detected faces (cleared each frame)
        self.face_detection_enabled = False  # Toggle for face detection mode
        self.cached_faces = []  # Cache face detections to avoid duplicate detectMultiScale calls
        self.cached_vision_mask = None  # Cache vision area mask for consistent processing
        
        # FPS tracking for face detection
        self.face_detection_fps = 0.0
        self.frame_times = []
        self.last_fps_update = time.time()

        # Laser detection components
        self.laser_finder = None
        self.laser_shooter = None
        self.laser_detection_enabled = False
        self.laser_detection_error = None  # Store initialization error for user display
        self.laser_coordinate = None
        self.raw_laser_coordinate = None
        self.smoothed_laser_coordinate = None
        self.laser_confidence = 0.0  # Store laser detection confidence
        self.laser_detection_fps = 0.0
        self.laser_frame_times = []
        self.last_laser_fps_update = time.time()
        self.targeted_players = []  # List of player indices that are being targeted by laser
        self.cached_player_details = []  # Cache player ID and confidence for display

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
            {"label": "Face detection test", "mode": "face_test"},
            {"label": "Laser detection test", "mode": "laser_test"},
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
        """Convert an OpenCV image to a pygame surface.
        
        COORDINATE SYSTEM NOTE:
        This method applies a horizontal flip for better user experience during setup.
        Users see a "mirror" view which feels more natural when drawing areas.
        However, coordinates drawn on this flipped display must be transformed
        before saving to match the gameplay coordinate system.
        """
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        cv_image = cv2.transpose(cv_image)  # transpose to match pygame orientation if needed
        surface = pygame.surfarray.make_surface(cv_image)
        surface = pygame.transform.flip(surface, True, False)  # Horizontal flip for setup UI
        return surface


    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    logger.info("Setup exit requested by user (Q key)")
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
                        elif self.current_mode == "face_test":
                            self.face_detection_enabled = True
                            self.current_faces = []
                            self.cached_faces = []  # Reset cached faces
                            self.face_extractor.reset_memory()
                            self.frame_times = []  # Reset FPS tracking
                            self.last_fps_update = time.time()
                        elif self.current_mode == "laser_test":
                            self.laser_detection_enabled = True
                            self.laser_coordinate = None
                            self.raw_laser_coordinate = None
                            self.smoothed_laser_coordinate = None
                            self.laser_confidence = 0.0
                            self.targeted_players = []
                            self.laser_frame_times = []  # Reset FPS tracking
                            self.last_laser_fps_update = time.time()
                            self.laser_detection_error = None  # Reset error state
                            # Initialize laser detection components
                            if self.laser_finder is None:
                                try:
                                    logger.info("Initializing LaserFinderNN for setup mode...")
                                    self.laser_finder = LaserFinderNN()
                                    if self.laser_finder.model is None:
                                        raise Exception("LaserFinderNN model failed to load")
                                    logger.info("LaserFinderNN initialized successfully")
                                except Exception as e:
                                    error_msg = f"Failed to initialize LaserFinderNN: {e}"
                                    logger.error(error_msg)
                                    self.laser_finder = None
                                    self.laser_detection_error = str(e)
                                    self.laser_detection_enabled = False  # Disable if failed to initialize
                            # Optional: Initialize laser shooter for testing (if IP provided)
                            # This can be uncommented if laser control is needed in setup mode
                            # if self.laser_shooter is None:
                            #     try:
                            #         self.laser_shooter = LaserShooter("192.168.45.50")
                            #     except Exception as e:
                            #         logger.warning(f"Failed to initialize LaserShooter: {e}")
                        else:
                            self.face_detection_enabled = False
                            self.laser_detection_enabled = False
                            self.cached_faces = []  # Clear cached faces when disabling
                            self.cached_vision_mask = None  # Clear cached mask when disabling
                            self.laser_coordinate = None
                            self.raw_laser_coordinate = None
                            self.smoothed_laser_coordinate = None
                            self.laser_confidence = 0.0
                            self.targeted_players = []
                            self.cached_player_details = []
                            self.laser_detection_error = None  # Clear error when switching modes
                        return

                if self.current_mode in self.reset_buttons:
                    if self.reset_buttons[self.current_mode].collidepoint(pos):
                        self.reset_area(self.current_mode)
                        logger.info(f"Reset {self.current_mode} area to default.")
                        return

                now = time.time()
                if now - self.last_click_time < 0.3 and self.current_mode != "settings" and self.current_mode in self.game_settings.areas:
                    # Double-click to delete: check collision directly with saved coordinates
                    # Only for modes that have area rectangles (not laser_test, face_test, nn_preview)
                    rects = self.game_settings.areas[self.current_mode].copy()
                    rects.reverse()  # Check from the last rectangle to the first
                    for rect in rects:
                        # Scale saved coordinates to screen coordinates for collision check
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
                # For area configuration modes, start drawing a new rectangle.
                elif self.current_mode in self.game_settings.areas:
                    self.drawing = True
                    # Convert global mouse position to feed-relative coordinates.
                    self.start_pos = (pos[0] - self.webcam_rect.x, pos[1] - self.webcam_rect.y)

            if event.type == pygame.MOUSEMOTION:
                if self.drawing and self.current_mode in self.game_settings.areas:
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
                # Only allow drawing rectangles for area configuration modes, not test modes
                if self.drawing and self.current_mode in self.game_settings.areas:
                    if self.current_rect and self.current_rect.width > 0 and self.current_rect.height > 0:
                        # Save coordinates directly as drawn on flipped display
                        self.game_settings.areas[self.current_mode].append(self.current_rect)
                        logger.debug(f"Added rectangle {self.current_rect} to {self.current_mode}.")
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

    def process_face_detection(self, webcam_frame: cv2.UMat):
        """Process frame for face detection and extract currently detected faces"""
        if not self.face_detection_enabled:
            return
            
        # Track frame timing for FPS calculation
        current_time = time.time()
        self.frame_times.append(current_time)
        
        # Keep only last 30 frame times for FPS calculation
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
            
        # Update FPS every second
        if current_time - self.last_fps_update >= 1.0:
            if len(self.frame_times) > 1:
                time_diff = self.frame_times[-1] - self.frame_times[0]
                if time_diff > 0:
                    self.face_detection_fps = (len(self.frame_times) - 1) / time_diff
            self.last_fps_update = current_time
            
        # Clear previous frame's faces - only show currently detected ones
        self.current_faces = []
            
        # Get vision area for face detection (use full frame if no vision area defined)
        # Use original setup areas directly since setup mode works in setup coordinate system
        vision_rects = self.game_settings.areas.get("vision", [])
        reference_surface = self.game_settings.get_reference_frame()
        
        # Create masked frame using vision area masking
        masked_frame = webcam_frame.copy()
        if vision_rects:
            # Create a mask for the vision area - zero out areas outside vision zones
            mask = cv2.cvtColor(webcam_frame, cv2.COLOR_BGR2GRAY)
            mask[:] = 0  # Initialize mask to zero
            
            for rect in vision_rects:
                # Skip invalid rectangles to prevent division by zero
                if reference_surface.w == 0 or reference_surface.h == 0 or rect.width == 0 or rect.height == 0:
                    continue
                    
                # Convert rect coordinates from setup space to frame coordinates
                # Setup coordinates are already in the correct orientation for setup mode
                x = int(rect.x / reference_surface.w * webcam_frame.shape[1])
                y = int(rect.y / reference_surface.h * webcam_frame.shape[0])
                w = int(rect.width / reference_surface.w * webcam_frame.shape[1])
                h = int(rect.height / reference_surface.h * webcam_frame.shape[0])
                
                # Ensure coordinates are within bounds
                x = max(0, min(x, webcam_frame.shape[1]))
                y = max(0, min(y, webcam_frame.shape[0]))
                w = max(0, min(w, webcam_frame.shape[1] - x))
                h = max(0, min(h, webcam_frame.shape[0] - y))
                
                if w > 0 and h > 0:
                    # The webcam display is horizontally flipped in setup mode (see convert_cv2_to_pygame)
                    # So we need to flip the x coordinate to match what the user sees
                    flipped_x = webcam_frame.shape[1] - (x + w)
                    flipped_x = max(0, flipped_x)  # Ensure x is not negative
                    # Draw the rectangle on the mask (white = allowed area)
                    cv2.rectangle(mask, (flipped_x, y), (flipped_x + w, y + h), 255, -1)
            
            # Apply the mask to the frame
            masked_frame = cv2.bitwise_and(webcam_frame, webcam_frame, mask=mask)
            
            # Store mask info for overlay drawing
            self.cached_vision_mask = mask
        else:
            self.cached_vision_mask = None
        
        # Use neural network to detect players first (same as main game)
        # Create a temporary NN frame from the masked webcam frame
        nn_frame = masked_frame
        
        # Run neural network detection to find players (same as main game)
        detected_players = self.neural_net.process_nn_frame(nn_frame, self.game_settings)
        
        # Cache both player and face bounding boxes for overlay drawing
        cached_player_boxes = []
        cached_player_details = []
        cached_face_boxes = []
        
        # Extract faces from detected players using FaceExtractor (same as main game)
        for player in detected_players:
            if player is not None:
                # Get player coordinates (same method as main game)
                player_coords = player.get_coords()
                player_id = player.get_id()
                
                # Store player bounding box for overlay
                x1, y1, x2, y2 = player_coords
                cached_player_boxes.append((x1, y1, x2 - x1, y2 - y1))
                
                # Store player details for overlay display
                cached_player_details.append({
                    'id': player_id,
                    'confidence': player.get_confidence()
                })
                
                # Use FaceExtractor.extract_face() with bounding box return - no duplication!
                result = self.face_extractor.extract_face(webcam_frame, player_coords, player_id, return_bbox=True)
                
                if result[0] is not None:  # face_crop is not None
                    face_crop, face_bbox = result
                    
                    # Store face for display
                    self.current_faces.append(face_crop)
                    
                    # Store face bounding box if we got coordinates
                    if face_bbox is not None:
                        face_x1, face_y1, fw, fh = face_bbox
                        cached_face_boxes.append((face_x1, face_y1, fw, fh))
        
        # Cache both player and face boxes for overlay drawing
        self.cached_player_boxes = cached_player_boxes
        self.cached_player_details = cached_player_details  # Store player details for face detection mode
        self.cached_faces = cached_face_boxes  # This now contains actual face boxes

    def process_laser_detection(self, webcam_frame: cv2.UMat):
        """Process frame for laser detection and player targeting"""
        if not self.laser_detection_enabled or self.laser_finder is None:
            return
            
        # Track frame timing for FPS calculation
        current_time = time.time()
        self.laser_frame_times.append(current_time)
        
        # Keep only last 30 frame times for FPS calculation
        if len(self.laser_frame_times) > 30:
            self.laser_frame_times.pop(0)
            
        # Update FPS every second
        if current_time - self.last_laser_fps_update >= 1.0:
            if len(self.laser_frame_times) > 1:
                time_diff = self.laser_frame_times[-1] - self.laser_frame_times[0]
                if time_diff > 0:
                    self.laser_detection_fps = (len(self.laser_frame_times) - 1) / time_diff
            self.last_laser_fps_update = current_time
            
        # Clear previous targeting
        self.targeted_players = []
        self.laser_coordinate = None
        self.raw_laser_coordinate = None
        self.smoothed_laser_coordinate = None
        self.laser_confidence = 0.0
        self.cached_player_details = []
        
        # Get vision area for laser detection (same logic as face detection - works with full frame)
        # Use original setup areas directly since setup mode works in setup coordinate system
        vision_rects = self.game_settings.areas.get("vision", [])
        reference_surface = self.game_settings.get_reference_frame()
        
        # Create masked frame using vision area masking (exactly same as face detection)
        masked_webcam_frame = webcam_frame.copy()
        if vision_rects:
            # Create a mask for the vision area - zero out areas outside vision zones
            mask = cv2.cvtColor(webcam_frame, cv2.COLOR_BGR2GRAY)
            mask[:] = 0  # Initialize mask to zero
            
            for rect in vision_rects:
                # Skip invalid rectangles to prevent division by zero
                if reference_surface.w == 0 or reference_surface.h == 0 or rect.width == 0 or rect.height == 0:
                    continue
                    
                # Convert rect coordinates from setup space to frame coordinates
                # Setup coordinates are already in the correct orientation for setup mode
                x = int(rect.x / reference_surface.w * webcam_frame.shape[1])
                y = int(rect.y / reference_surface.h * webcam_frame.shape[0])
                w = int(rect.width / reference_surface.w * webcam_frame.shape[1])
                h = int(rect.height / reference_surface.h * webcam_frame.shape[0])
                
                # Ensure coordinates are within bounds
                x = max(0, min(x, webcam_frame.shape[1]))
                y = max(0, min(y, webcam_frame.shape[0]))
                w = max(0, min(w, webcam_frame.shape[1] - x))
                h = max(0, min(h, webcam_frame.shape[0] - y))
                
                if w > 0 and h > 0:
                    # The webcam display is horizontally flipped in setup mode (see convert_cv2_to_pygame)
                    # So we need to flip the x coordinate to match what the user sees
                    flipped_x = webcam_frame.shape[1] - (x + w)
                    flipped_x = max(0, flipped_x)  # Ensure x is not negative
                    # Draw the rectangle on the mask (white = allowed area)
                    cv2.rectangle(mask, (flipped_x, y), (flipped_x + w, y + h), 255, -1)
            
            # Apply the mask to the frame
            masked_webcam_frame = cv2.bitwise_and(webcam_frame, webcam_frame, mask=mask)
        
        # Use neural network to detect players first (same as face detection mode)
        # Create a temporary NN frame from the masked webcam frame
        nn_frame = masked_webcam_frame
        
        # Run neural network detection to find players (same as face detection mode)
        detected_players = self.neural_net.process_nn_frame(nn_frame, self.game_settings)
        
        # Cache player bounding boxes and details for overlay drawing
        cached_player_boxes = []
        cached_player_details = []
        for player in detected_players:
            if player is not None:
                player_coords = player.get_coords()
                x1, y1, x2, y2 = player_coords
                cached_player_boxes.append((x1, y1, x2 - x1, y2 - y1))
                cached_player_details.append({
                    'id': player.get_id(),
                    'confidence': player.get_confidence()
                })
        
        self.cached_player_boxes = cached_player_boxes
        self.cached_player_details = cached_player_details
        
        # Run laser detection using LaserFinderNN with full-resolution masked frame
        try:
            laser_coord, output_image = self.laser_finder.find_laser(masked_webcam_frame, [], nn_frame)
            
            if self.laser_finder.laser_found() and laser_coord is not None:
                # Get both raw and smoothed coordinates directly from filter
                self.raw_laser_coordinate = self.laser_finder.get_raw_coord()
                self.smoothed_laser_coordinate = self.laser_finder.get_smoothed_coord()
                
                
                # Use smoothed coordinate as primary (for compatibility with targeting logic)
                self.laser_coordinate = self.smoothed_laser_coordinate or self.raw_laser_coordinate
                
                # Get confidence from the best detection
                if hasattr(self.laser_finder, 'get_all_detections'):
                    # Neural network laser finder has confidence
                    all_detections = self.laser_finder.get_all_detections()
                    if all_detections:
                        best_detection = max(all_detections, key=lambda d: d['confidence'])
                        self.laser_confidence = best_detection['confidence']
                    else:
                        self.laser_confidence = 0.0
                else:
                    # Traditional laser finder doesn't have confidence
                    self.laser_confidence = 1.0
                
                # Check for player-laser intersection (same criteria as shooting control loop)
                for idx, (px, py, pw, ph) in enumerate(cached_player_boxes):
                    # Check if laser coordinate is within player bounding box
                    laser_x, laser_y = laser_coord
                    if px <= laser_x <= px + pw and py <= laser_y <= py + ph:
                        self.targeted_players.append(idx)
                        
        except Exception as e:
            logger.error(f"Laser detection error: {e}")
            self.laser_coordinate = None
            self.raw_laser_coordinate = None
            self.smoothed_laser_coordinate = None

    def draw_detected_faces(self):
        """Draw currently detected faces at the bottom of the screen"""
        if not self.current_faces or self.current_mode != "face_test":
            return
            
        face_size = 80  # Size of each face thumbnail
        margin = 10
        start_x = 20
        start_y = self.screen_height - face_size - 20
        
        # Draw background for face area
        face_area_width = len(self.current_faces) * (face_size + margin) + margin
        face_bg_rect = pygame.Rect(start_x - 5, start_y - 25, face_area_width, face_size + 30)
        pygame.draw.rect(self.screen, (50, 50, 50, 180), face_bg_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), face_bg_rect, 2)
        
        # Label for face detection area
        label_text = f"Currently Detected Faces ({len(self.current_faces)})"
        label_surf = self.font.render(label_text, True, (255, 255, 255))
        self.screen.blit(label_surf, (start_x, start_y - 20))
        
        # Draw each currently detected face
        for idx, face in enumerate(self.current_faces):
            x_pos = start_x + idx * (face_size + margin)
            
            # Convert OpenCV image to pygame surface
            face_rgb = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face_surface = pygame.surfarray.make_surface(face_rgb.swapaxes(0, 1))
            face_surface = pygame.transform.scale(face_surface, (face_size, face_size))
            
            # Draw face with border
            face_rect = pygame.Rect(x_pos, start_y, face_size, face_size)
            pygame.draw.rect(self.screen, (255, 255, 255), face_rect, 2)
            self.screen.blit(face_surface, (x_pos, start_y))

    def draw_face_detection_overlay(self, webcam_frame: cv2.UMat):
        """Draw player and face detection rectangles on the webcam feed"""
        if not self.face_detection_enabled:
            return
        
        # Use unified method to draw player bounding boxes with details
        player_boxes = getattr(self, 'cached_player_boxes', [])
        player_details = getattr(self, 'cached_player_details', None)
        self.draw_player_bboxes_with_info(
            player_boxes=player_boxes,
            player_details=player_details,  # Face mode now shows player details too
            targeted_indices=None,
            display_mode="face_test"
        )
        
        # Draw face bounding boxes in green (on top of player boxes)
        faces = self.cached_faces
        for (fx, fy, fw, fh) in faces:
            # Convert to screen coordinates
            x = int(fx * self.webcam_to_screen_ratio)
            y = int(fy * self.webcam_to_screen_ratio)
            w = int(fw * self.webcam_to_screen_ratio)
            h = int(fh * self.webcam_to_screen_ratio)
            
            # Flip the x coordinate to match pygame orientation (same as neural net preview)
            x = self.webcam_rect.width - x - w
            
            # Apply webcam rect offset
            screen_x = x + self.webcam_rect.x
            screen_y = y + self.webcam_rect.y
            screen_w = w
            screen_h = h
            
            # Draw face detection rectangle in bright green
            pygame.draw.rect(self.screen, (0, 255, 0), (screen_x, screen_y, screen_w, screen_h), 3)
            # Draw center point
            center_x = screen_x + screen_w // 2
            center_y = screen_y + screen_h // 2
            pygame.draw.circle(self.screen, (255, 0, 0), (center_x, center_y), 5)

    def draw_player_bboxes_with_info(self, player_boxes, player_details=None, targeted_indices=None, display_mode="default", surface_coords=False, surface_offset=(0, 0)):
        """
        Unified method to draw player bounding boxes with information across different setup modes.
        
        Args:
            player_boxes: List of (x, y, width, height) tuples 
            player_details: Optional list of {'id': player_id, 'confidence': confidence} dicts
            targeted_indices: Optional list of player indices that are targeted (for laser mode)
            display_mode: "nn_preview", "face_test", "laser_test", or "default"
            surface_coords: If True, player_boxes are already in surface coordinates (for nn_preview)
            surface_offset: Offset to apply when using surface_coords (x_offset, y_offset)
        """
        if not player_boxes:
            return
        
        for idx, (px, py, pw, ph) in enumerate(player_boxes):
            if surface_coords:
                # Already in surface coordinates (nn_preview mode)
                screen_x = px + surface_offset[0]
                screen_y = py + surface_offset[1]
                screen_w, screen_h = pw, ph
            else:
                # Convert from webcam frame coordinates to screen coordinates
                x = int(px * self.webcam_to_screen_ratio)
                y = int(py * self.webcam_to_screen_ratio)
                w = int(pw * self.webcam_to_screen_ratio)
                h = int(ph * self.webcam_to_screen_ratio)
                
                # Flip the x coordinate to match pygame orientation
                x = self.webcam_rect.width - x - w
                
                # Apply webcam rect offset
                screen_x = x + self.webcam_rect.x
                screen_y = y + self.webcam_rect.y
                screen_w = w
                screen_h = h
            
            # Get player details if available
            player_detail = player_details[idx] if player_details and idx < len(player_details) else None
            player_id = player_detail['id'] if player_detail else f"P{idx}"
            player_confidence = player_detail['confidence'] if player_detail else 0.0
            
            # Check if this player is being targeted (laser mode only)
            is_targeted = targeted_indices and idx in targeted_indices
            
            # Determine colors and styling based on mode and targeting
            if display_mode == "laser_test" and is_targeted:
                # Targeted player in laser mode
                bbox_color = (255, 0, 0)  # Red
                bbox_thickness = 4
                text_color = (255, 255, 255)  # White
                
                # Draw red tint overlay for targeted players
                target_overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
                target_overlay.fill((255, 0, 0, 80))  # Semi-transparent red
                self.screen.blit(target_overlay, (screen_x, screen_y))
                
                # Add "TARGET LOCKED" text
                target_text = self.font.render("TARGET LOCKED", True, (255, 255, 255))
                text_bg = pygame.Surface((target_text.get_width() + 4, target_text.get_height() + 2), pygame.SRCALPHA)
                text_bg.fill((255, 0, 0, 200))  # Semi-transparent red background
                text_x = screen_x + max(0, (screen_w - target_text.get_width()) // 2)
                text_y = screen_y - 25
                self.screen.blit(text_bg, (text_x - 2, text_y - 1))
                self.screen.blit(target_text, (text_x, text_y))
                
            elif display_mode == "nn_preview":
                # Neural network preview mode styling
                bbox_thickness = 3
                text_color = (255, 255, 255)  # White text
                
                # Color code bounding box based on confidence
                if player_confidence >= 0.8:
                    bbox_color = (0, 255, 0)  # Bright green
                elif player_confidence >= 0.6:
                    bbox_color = (128, 255, 0)  # Yellow-green
                elif player_confidence >= 0.4:
                    bbox_color = (255, 165, 0)  # Orange
                else:
                    bbox_color = (255, 0, 0)  # Red
                    
            elif display_mode == "face_test":
                # Face detection mode - simple blue boxes
                bbox_color = (0, 100, 255)  # Blue
                bbox_thickness = 2
                text_color = (0, 255, 255)  # Cyan
                
            else:
                # Default styling (laser_test non-targeted, other modes)
                bbox_color = (0, 100, 255)  # Blue
                bbox_thickness = 2
                text_color = (0, 255, 255)  # Cyan
            
            # Draw the bounding box
            pygame.draw.rect(self.screen, bbox_color, (screen_x, screen_y, screen_w, screen_h), bbox_thickness)
            
            # Draw player information text (if we have details or it's appropriate for the mode)
            show_info = display_mode in ["nn_preview", "laser_test", "face_test"] and player_details
            
            if show_info:
                # Get confidence for color coding
                conf_percentage = int(player_confidence * 100)
                
                # Color code confidence text based on confidence level
                if player_confidence >= 0.8:
                    conf_color = (0, 255, 0)  # Bright green
                elif player_confidence >= 0.6:
                    conf_color = (128, 255, 0)  # Yellow-green
                elif player_confidence >= 0.4:
                    conf_color = (255, 165, 0)  # Orange
                else:
                    conf_color = (255, 0, 0)  # Red
                
                # Draw semi-transparent background for text
                text_bg_height = 35
                text_bg = pygame.Surface((max(80, screen_w), text_bg_height), pygame.SRCALPHA)
                text_bg.fill((0, 0, 0, 180))  # Semi-transparent black
                
                # Position text above the bounding box (or below if no room above)
                text_y_pos = screen_y - text_bg_height if screen_y - text_bg_height > 0 else screen_y + screen_h
                self.screen.blit(text_bg, (screen_x, text_y_pos))
                
                # Draw the player ID
                id_surf = self.font.render(f"ID:{player_id}", True, text_color)
                self.screen.blit(id_surf, (screen_x + 2, text_y_pos + 2))
                
                # Draw confidence percentage with color coding (if we have confidence data)
                if player_detail:
                    conf_surf = self.font.render(f"{conf_percentage}%", True, conf_color)
                    self.screen.blit(conf_surf, (screen_x + 2, text_y_pos + 17))

    def draw_laser_detection_overlay(self, webcam_frame: cv2.UMat):
        """Draw player bounding boxes and laser detection visualization"""
        if not self.laser_detection_enabled:
            return
        
        # Use unified method to draw player bounding boxes with targeting info
        player_boxes = getattr(self, 'cached_player_boxes', [])
        player_details = getattr(self, 'cached_player_details', None)
        targeted_indices = getattr(self, 'targeted_players', [])
        
        self.draw_player_bboxes_with_info(
            player_boxes=player_boxes,
            player_details=player_details, 
            targeted_indices=targeted_indices,
            display_mode="laser_test"
        )
        
        # Draw laser dots if detected (both raw and smoothed)
        def convert_coord_to_screen(coord):
            """Helper to convert laser coordinate to screen position"""
            if coord is None:
                return None
            x, y = coord
            screen_x = int(x * self.webcam_to_screen_ratio)
            screen_y = int(y * self.webcam_to_screen_ratio)
            # Flip the x coordinate to match pygame orientation
            screen_x = self.webcam_rect.width - screen_x
            # Apply webcam rect offset
            final_x = screen_x + self.webcam_rect.x
            final_y = screen_y + self.webcam_rect.y
            return (final_x, final_y)
        
        # Draw raw coordinate (smaller, cyan) - only when actively detecting
        if self.raw_laser_coordinate is not None:
            raw_screen_pos = convert_coord_to_screen(self.raw_laser_coordinate)
            if raw_screen_pos:
                final_x, final_y = raw_screen_pos
                # Raw laser dot (cyan, smaller)
                pygame.draw.circle(self.screen, (0, 255, 255), (final_x, final_y), 5)
                pygame.draw.circle(self.screen, (255, 255, 255), (final_x, final_y), 5, 1)
                
                # Small crosshairs for raw
                crosshair_size = 10
                pygame.draw.line(self.screen, (0, 255, 255), 
                               (final_x - crosshair_size, final_y), 
                               (final_x + crosshair_size, final_y), 2)
                pygame.draw.line(self.screen, (0, 255, 255), 
                               (final_x, final_y - crosshair_size), 
                               (final_x, final_y + crosshair_size), 2)
        
        # Draw smoothed coordinate (larger, yellow) - persists in memory even without current detection
        if self.smoothed_laser_coordinate is not None:
            smooth_screen_pos = convert_coord_to_screen(self.smoothed_laser_coordinate)
            if smooth_screen_pos:
                final_x, final_y = smooth_screen_pos
                
                # Determine if this is a memory position (no current raw detection)
                is_memory = self.raw_laser_coordinate is None
                
                if is_memory:
                    # Memory position - dimmed yellow with dashed crosshairs
                    color = (180, 180, 0)  # Dimmed yellow
                    pygame.draw.circle(self.screen, color, (final_x, final_y), 8)
                    pygame.draw.circle(self.screen, (150, 150, 150), (final_x, final_y), 8, 2)  # Dimmed white border
                    
                    # Dashed crosshairs for memory position
                    crosshair_size = 15
                    dash_length = 4
                    for i in range(0, crosshair_size, dash_length * 2):
                        # Horizontal dashes
                        dash_start_x = final_x - crosshair_size + i
                        dash_end_x = min(final_x + crosshair_size, dash_start_x + dash_length)
                        if dash_start_x < final_x + crosshair_size:
                            pygame.draw.line(self.screen, color, 
                                           (dash_start_x, final_y), (dash_end_x, final_y), 3)
                        # Vertical dashes
                        dash_start_y = final_y - crosshair_size + i
                        dash_end_y = min(final_y + crosshair_size, dash_start_y + dash_length)
                        if dash_start_y < final_y + crosshair_size:
                            pygame.draw.line(self.screen, color, 
                                           (final_x, dash_start_y), (final_x, dash_end_y), 3)
                else:
                    # Active smoothed position - bright yellow
                    pygame.draw.circle(self.screen, (255, 255, 0), (final_x, final_y), 8)
                    pygame.draw.circle(self.screen, (255, 255, 255), (final_x, final_y), 8, 2)
                    
                    # Solid crosshairs for active position
                    crosshair_size = 15
                    pygame.draw.line(self.screen, (255, 255, 0), 
                                   (final_x - crosshair_size, final_y), 
                                   (final_x + crosshair_size, final_y), 3)
                    pygame.draw.line(self.screen, (255, 255, 0), 
                                   (final_x, final_y - crosshair_size), 
                                   (final_x, final_y + crosshair_size), 3)
        
        # Use smoothed coordinate for text display (or raw if smoothed not available)
        text_coord = self.smoothed_laser_coordinate or self.raw_laser_coordinate
        if text_coord is not None:
            text_screen_pos = convert_coord_to_screen(text_coord)
            if text_screen_pos:
                final_x, final_y = text_screen_pos
            
            # Draw laser coordinates and confidence text
            # Show both raw and smoothed coordinates
            raw_text = ""
            smooth_text = ""
            
            if self.raw_laser_coordinate:
                try:
                    raw_x, raw_y = self.raw_laser_coordinate
                    raw_text = f"Raw: ({int(raw_x)}, {int(raw_y)})"
                except (ValueError, TypeError, IndexError):
                    raw_text = f"Raw: {self.raw_laser_coordinate}"
            
            if self.smoothed_laser_coordinate:
                try:
                    smooth_x, smooth_y = self.smoothed_laser_coordinate
                    smooth_text = f"Smooth: ({int(smooth_x)}, {int(smooth_y)})"
                except (ValueError, TypeError, IndexError):
                    smooth_text = f"Smooth: {self.smoothed_laser_coordinate}"
            
            # Safely format confidence - handle potential string values
            try:
                confidence_value = float(self.laser_confidence) if self.laser_confidence is not None else 0.0
                confidence_text = f"Conf: {confidence_value:.3f}"
            except (ValueError, TypeError):
                confidence_text = f"Conf: {self.laser_confidence}"
            
            # Create surfaces for all texts
            surfaces = []
            colors = []
            
            if raw_text:
                raw_surf = self.font.render(raw_text, True, (0, 255, 255))  # Cyan for raw
                surfaces.append(raw_surf)
                colors.append((0, 255, 255))
            
            if smooth_text:
                # Check if smoothed coordinate is from memory (no current raw detection)
                is_memory = self.raw_laser_coordinate is None
                if is_memory:
                    smooth_text += " (memory)"
                    smooth_surf = self.font.render(smooth_text, True, (180, 180, 0))  # Dimmed yellow for memory
                    surfaces.append(smooth_surf)
                    colors.append((180, 180, 0))
                else:
                    smooth_surf = self.font.render(smooth_text, True, (255, 255, 0))  # Yellow for active smoothed
                    surfaces.append(smooth_surf)
                    colors.append((255, 255, 0))
            
            conf_surf = self.font.render(confidence_text, True, (0, 255, 0))  # Green for confidence
            surfaces.append(conf_surf)
            colors.append((0, 255, 0))
            
            # Calculate background size
            max_width = max(surf.get_width() for surf in surfaces) if surfaces else 0
            total_height = sum(surf.get_height() + 2 for surf in surfaces) if surfaces else 0
            text_bg = pygame.Surface((max_width + 8, total_height), pygame.SRCALPHA)
            text_bg.fill((0, 0, 0, 180))  # Semi-transparent black background
            
            coord_x = final_x + 15
            coord_y = final_y - 60  # Move up to accommodate more text
            
            # Draw background
            self.screen.blit(text_bg, (coord_x - 2, coord_y - 1))
            
            # Draw all text lines
            current_y = coord_y
            for surf in surfaces:
                self.screen.blit(surf, (coord_x, current_y))
                current_y += surf.get_height() + 2

    def draw_ui(self, webcam_surf: pygame.Surface, webcam_frame: cv2.UMat):

        self.screen.fill(PINK)

        # Process face detection if in face test mode
        if self.current_mode == "face_test":
            self.process_face_detection(webcam_frame)
        
        # Process laser detection if in laser test mode
        if self.current_mode == "laser_test":
            self.process_laser_detection(webcam_frame)

        if self.current_mode == "nn_preview":
            # Apply the vision frame to the webcam surface
            # Create temporary settings with coordinates transformed for camera processing
            temp_settings = GameSettings()
            temp_settings.params = self.game_settings.params
            temp_settings.reference_frame = self.game_settings.reference_frame
            
            # Transform CURRENT setup coordinates to gameplay coordinates for camera cropping
            # This ensures NN preview uses current (unsaved) settings, not cached saved settings
            temp_settings.areas = {}
            frame_width = self.game_settings.reference_frame[0]
            
            for area_name, rect_list in self.game_settings.areas.items():
                gameplay_rects = []
                for rect in rect_list:
                    # Transform x-coordinate from setup space to gameplay space (same as GameSettings.get_gameplay_areas)
                    gameplay_x = frame_width - (rect.x + rect.width)
                    # Y-coordinate and dimensions remain the same
                    gameplay_rect = pygame.Rect(gameplay_x, rect.y, rect.width, rect.height)
                    gameplay_rects.append(gameplay_rect)
                temp_settings.areas[area_name] = gameplay_rects
            
            nn_frame, webcam_frame, rect = self.camera.read_nn(temp_settings, self.neural_net.get_max_size())

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

                # Only log occasionally to avoid spam
                if hasattr(self, '_frame_log_count'):
                    self._frame_log_count += 1
                else:
                    self._frame_log_count = 1
                    
                if self._frame_log_count % 60 == 0:  # Log every 60 frames
                    logger.debug(
                        f"Frame info: {webcam_frame.shape[1]}x{webcam_frame.shape[0]} → {nn_frame.shape[1]}x{nn_frame.shape[0]}, screen: {new_width}x{new_height}"
                    )
                nn_surf_resized = pygame.transform.scale(nn_surf, (new_width, new_height))
                # Center the resized surface
                x_offset = (self.screen_width - new_width) // 2
                y_offset = (self.screen_height - new_height) // 2

                # Run the model and highlight detections - use same settings format as game mode  
                players = self.neural_net.process_nn_frame(nn_frame, self.game_settings)
                
                # Calculate statistics for label
                detection_count = len([p for p in players if p is not None])
                confidences = [p.get_confidence() for p in players if p is not None]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                for p in players:
                    if p is not None:
                        bbox = p.get_bbox()
                        # Now apply scaling factors from NN Frame to webcam frame AND from webcam frame to resized surface
                        x = int(bbox[0] * new_width / rect.width * rect.width / nn_frame.shape[1])
                        y = int(bbox[1] * new_height / rect.height * rect.height / nn_frame.shape[0])
                        w = int(bbox[2] * new_width / rect.width * rect.width / nn_frame.shape[1])
                        h = int(bbox[3] * new_height / rect.height * rect.height / nn_frame.shape[0])
                        # Flip the x coordinate to match pygame orientation
                        x = new_width - x - w
                        # Only log player bbox occasionally to reduce spam
                        if self._frame_log_count % 60 == 0:
                            logger.debug(f"Player ID: {p.get_id()} bbox: {bbox} scaled:{(x, y, w, h)} conf: {p.get_confidence():.2f}")

                        # Get confidence for color coding
                        confidence = p.get_confidence()
                        conf_percentage = int(confidence * 100)
                        
                        # Color code bounding box based on confidence
                        # High confidence (80-100%): Bright green
                        # Medium confidence (60-79%): Yellow-green  
                        # Low confidence (40-59%): Orange
                        # Very low confidence (<40%): Red
                        if confidence >= 0.8:
                            bbox_color = (0, 255, 0)  # Bright green
                            text_color = (0, 255, 0)
                        elif confidence >= 0.6:
                            bbox_color = (128, 255, 0)  # Yellow-green
                            text_color = (128, 255, 0)
                        elif confidence >= 0.4:
                            bbox_color = (255, 165, 0)  # Orange
                            text_color = (255, 165, 0)
                        else:
                            bbox_color = (255, 0, 0)  # Red
                            text_color = (255, 0, 0)
                        
                        # Draw the bounding box around the detected player with confidence-based color
                        pygame.draw.rect(nn_surf_resized, bbox_color, (x, y, w, h), 3)
                        
                        # Draw semi-transparent background for text
                        text_bg_height = 35
                        text_bg = pygame.Surface((max(80, w), text_bg_height), pygame.SRCALPHA)
                        text_bg.fill((0, 0, 0, 180))  # Semi-transparent black
                        nn_surf_resized.blit(text_bg, (x, y - text_bg_height))
                        
                        # Draw the player ID
                        id_surf = self.font.render(f"ID:{p.get_id()}", True, text_color)
                        nn_surf_resized.blit(id_surf, (x + 2, y - text_bg_height + 2))
                        
                        # Draw confidence percentage with color coding
                        conf_surf = self.font.render(f"{conf_percentage}%", True, text_color)
                        nn_surf_resized.blit(conf_surf, (x + 2, y - text_bg_height + 17))

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
        elif self.current_mode == "face_test":
            # Resize the webcam surface to fit the screen
            webcam_surf = pygame.transform.scale(webcam_surf, (self.webcam_rect.w, self.webcam_rect.h))
            
            # Draw the webcam feed for face detection
            self.screen.blit(webcam_surf, self.webcam_rect.topleft)
            
            # Draw face detection rectangles on the webcam feed
            self.draw_face_detection_overlay(webcam_frame)
            
            # Draw a rectangle around the face test preview
            pygame.draw.rect(self.screen, (0, 255, 255), self.webcam_rect, 2)
            # Add a label with FPS
            label_surf = self.font.render(
                f"Face Detection Test - Detected: {len(self.current_faces)} faces, FPS: {self.face_detection_fps:.1f}",
                True,
                (255, 255, 255),
            )
            label_rect = label_surf.get_rect(center=(self.webcam_rect.centerx, self.webcam_rect.y - 20))
            self.screen.blit(label_surf, label_rect.topleft)
        elif self.current_mode == "laser_test":
            # Check if there's a laser detection error to display
            if self.laser_detection_error is not None:
                # Show error screen instead of normal laser test interface
                self.screen.fill((50, 50, 50))  # Dark gray background
                
                # Draw error title
                error_title = self.big_font.render("LASER DETECTION ERROR", True, (255, 50, 50))
                title_rect = error_title.get_rect(center=(self.screen_width // 2, self.screen_height // 2 - 100))
                self.screen.blit(error_title, title_rect.topleft)
                
                # Draw error details
                error_lines = [
                    "LaserFinderNN failed to initialize:",
                    f"Error: {self.laser_detection_error}",
                    "",
                    "Common causes:",
                    "• Missing laser model file (.pt, .onnx, .engine)",
                    "• PyTorch not installed or not available",
                    "• Model file corrupted or incompatible",
                    "",
                    "Expected model file:",
                    "yolov5l6_e200_b8_tvt302010_laser_v5.pt",
                    "",
                    "Check logs above for more details."
                ]
                
                y_offset = self.screen_height // 2 - 20
                for line in error_lines:
                    if line.startswith("Error:"):
                        color = (255, 100, 100)  # Light red for error message
                    elif line.startswith("•") or line.endswith(".pt"):
                        color = (255, 255, 150)  # Light yellow for details
                    else:
                        color = (200, 200, 200)  # Light gray for normal text
                    
                    if line:  # Skip empty lines for rendering
                        text_surf = self.font.render(line, True, color)
                        text_rect = text_surf.get_rect(center=(self.screen_width // 2, y_offset))
                        self.screen.blit(text_surf, text_rect.topleft)
                    y_offset += 25
                
                # Add instruction to switch modes
                switch_instruction = "Click another mode to continue setup"
                instruction_surf = self.font.render(switch_instruction, True, (100, 255, 100))
                instruction_rect = instruction_surf.get_rect(center=(self.screen_width // 2, self.screen_height - 50))
                self.screen.blit(instruction_surf, instruction_rect.topleft)
            else:
                # Normal laser test interface (no errors)
                # Resize the webcam surface to fit the screen
                webcam_surf = pygame.transform.scale(webcam_surf, (self.webcam_rect.w, self.webcam_rect.h))
                
                # Draw the webcam feed for laser detection testing
                self.screen.blit(webcam_surf, self.webcam_rect.topleft)
                
                # Draw laser detection overlays (players, laser dot, targeting)
                self.draw_laser_detection_overlay(webcam_frame)
                
                # Draw a rectangle around the laser test preview
                pygame.draw.rect(self.screen, (255, 165, 0), self.webcam_rect, 2)  # Orange border
                
                # Prepare status information
                if self.laser_coordinate:
                    laser_status = f"DETECTED (conf: {self.laser_confidence:.3f})"
                else:
                    laser_status = "NOT DETECTED"
                target_count = len(self.targeted_players)
                target_status = f"TARGETING {target_count} PLAYER(S)" if target_count > 0 else "NO TARGETS"
                
                # Add comprehensive label with detection and targeting status
                label_parts = [
                    f"Laser Detection Test - FPS: {self.laser_detection_fps:.1f}",
                    f"Laser: {laser_status}",
                    f"Players: {len(self.cached_player_boxes) if hasattr(self, 'cached_player_boxes') else 0}",
                    target_status
                ]
                full_label = " | ".join(label_parts)
                
                label_surf = self.font.render(full_label, True, (255, 255, 255))
                label_rect = label_surf.get_rect(center=(self.webcam_rect.centerx, self.webcam_rect.y - 20))
                self.screen.blit(label_surf, label_rect.topleft)
                
                # Add instructions for manual laser testing
                if not hasattr(self, '_instruction_shown') or self.current_mode == "laser_test":
                    instruction_text = "Point a laser manually at players to test targeting detection"
                    instruction_surf = self.font.render(instruction_text, True, (255, 200, 0))
                    instruction_rect = instruction_surf.get_rect(center=(self.webcam_rect.centerx, self.webcam_rect.bottom + 20))
                    self.screen.blit(instruction_surf, instruction_rect.topleft)
                    self._instruction_shown = True
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
                # Draw rectangles directly as saved
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

        # Draw detected faces at the bottom (for face test mode)
        self.draw_detected_faces()
        
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
