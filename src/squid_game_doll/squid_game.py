from threading import Thread
import pygame
import cv2
import random
import time
from .game_screen import GameScreen
from .base_player_tracker import BasePlayerTracker
from .player_tracker_ul import PlayerTrackerUL
from .player import Player
from .face_extractor import FaceExtractor
from .game_camera import GameCamera
from .cuda_utils import is_cuda_opencv_available
from .laser_shooter import LaserShooter
from .laser_tracker import LaserTracker
from .game_settings import GameSettings
from .utils.platform import (
    is_jetson_orin,
    is_raspberry_pi,
    should_use_hailo,
    get_platform_info
)
from .constants import (
    ROOT,
    DARK_GREEN,
    MINIMUM_RED_LIGHT_S,
    MINIMUM_GREEN_LIGHT_S,
    GRACE_PERIOD_RED_LIGHT_S,
    INIT,
    RED_LIGHT,
    GREEN_LIGHT,
    LOADING,
    GAMEOVER,
    VICTORY,
    WHITE,
)
import platform
from loguru import logger


class SquidGame:
    def __init__(
        self,
        disable_tracker: bool,
        desktop_size: tuple[int, int],
        display_idx: int,
        ip: str,
        joystick: pygame.joystick.JoystickType,
        cam: GameCamera,
        model: str,
        settings: GameSettings,
    ) -> None:
        self.previous_time: float = time.time()
        self.previous_positions: list = []  # List of bounding boxes (tuples)
        self.tracker: BasePlayerTracker = None  # Initialize later
        self.FAKE: bool = False
        self.face_extractor: FaceExtractor = FaceExtractor()  # Initialize later
        self.players: list[Player] = []
        self.green_sound: pygame.mixer.Sound = pygame.mixer.Sound(ROOT + "/media/green_light.mp3")
        # 무궁화 꽃이 피었습니다
        self.red_sound: pygame.mixer.Sound = pygame.mixer.Sound(ROOT + "/media/red_light.mp3")
        self.eliminate_sound: pygame.mixer.Sound = pygame.mixer.Sound(ROOT + "/media/eliminated.mp3")
        self.init_sound: pygame.mixer.Sound = pygame.mixer.Sound(ROOT + "/media/init.mp3")
        self.victory_sound: pygame.mixer.Sound = pygame.mixer.Sound(ROOT + "/media/success.mp3")
        self.gunshot_sound: pygame.mixer.Sound = pygame.mixer.Sound(ROOT + "/media/gunshot.mp3")
        self.game_state: str = INIT
        self.last_switch_time: float = time.time()
        self.delay_s: float = 1.0
        self.game_screen = GameScreen(desktop_size, display_idx)
        self.no_tracker: bool = disable_tracker
        self.shooter: LaserShooter = None
        self.laser_tracker: LaserTracker = None
        self.joystick: pygame.joystick.JoystickType = joystick
        self.start_registration = time.time()
        self._init_done = False
        self.intro_sound: pygame.mixer.Sound = pygame.mixer.Sound(ROOT + "/media/flute.mp3")
        self.cam: GameCamera = cam
        self.settings: GameSettings = settings
        self.model: str = model
        if not self.no_tracker:
            self.shooter = LaserShooter(ip)
            self.laser_tracker = LaserTracker(self.shooter)

        logger.info(
            f"SquidGame(res={desktop_size} on #{display_idx}, tracker disabled={disable_tracker} (ip={ip}), joystick={self.joystick is not None})"
        )

    def switch_to_init(self) -> bool:
        logger.info("Switch to INIT")
        self.game_state = INIT
        self.cam.reinit()
        self.players.clear()
        self.last_switch_time = time.time()
        self.green_sound.stop()
        self.red_sound.stop()
        self.eliminate_sound.stop()
        self.intro_sound.stop()
        self.init_sound.play()
        self.start_registration = time.time()
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        self.face_extractor.reset_memory()
        if not self.no_tracker:
            self.shooter.set_eyes(False)
            self.shooter.rotate_head(False)
        return True

    def switch_to_redlight(self) -> bool:
        logger.info("Switch to REDLIGHT")
        if not self.no_tracker:
            self.shooter.set_eyes(True)
            self.shooter.rotate_head(False)
        self.last_switch_time = time.time() + GRACE_PERIOD_RED_LIGHT_S
        self.game_state = RED_LIGHT
        self.green_sound.stop()
        self.red_sound.play()
        self.delay_s = random.random() * 6 + MINIMUM_RED_LIGHT_S
        return True

    def switch_to_greenlight(self) -> bool:
        logger.info("Switch to GREENLIGHT")
        if not self.no_tracker:
            self.shooter.set_eyes(False)
            self.shooter.rotate_head(True)
        self.last_switch_time = time.time()
        self.game_state = GREEN_LIGHT
        self.green_sound.play()
        self.red_sound.stop()
        self.delay_s = random.random() * 4 + MINIMUM_GREEN_LIGHT_S
        return True

    def switch_to_game(self) -> bool:
        logger.info("Switch to GAME")
        pygame.time.delay(1000)
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        return self.switch_to_greenlight()

    def switch_to_loading(self) -> bool:
        logger.info("Switch to LOADING")
        self.game_state = LOADING
        self.last_switch_time = time.time()
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        return True

    def switch_to_endgame(self, endgame_str: str) -> bool:
        logger.info("Switch to ENDGAME")
        self.game_state = endgame_str
        if endgame_str == VICTORY:
            self.victory_sound.play()
        self.last_switch_time = time.time()
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_loading)
        if not self.no_tracker:
            self.shooter.rotate_head(False)
            self.shooter.set_eyes(False)
        return True

    def close_loading_screen(self) -> bool:
        logger.debug("close_loading_screen")
        self.game_state = INIT
        return False

    def check_endgame_conditions(self, crop_info: pygame.Rect, nn_frame: cv2.UMat, screen: cv2.UMat) -> None:
        """
        Checks each player to see if they have reached the finish area.
        Then, if every player is either a winner or eliminated, switches the game state to VICTORY.
        """
        for player in self.players:
            # Only consider players not already eliminated or marked as winner.
            if not player.is_eliminated() and not player.is_winner():
                # Convert player rectangle from nn frame to webcam frame coordinates (where areas rectangles are expressed)
                player_rect = GameCamera.convert_nn_to_screen_coord(player.get_rect(), nn_frame, crop_info, 1.0)

                # If player has reached the finish area,
                # mark the player as a winner. At least two seconds after last transition.
                if (
                    GameCamera.intersect(player_rect, self.settings.get_gameplay_areas()["finish"])
                    and time.time() - self.last_switch_time > 2
                ):
                    player.set_winner()

        # Update game state
        if self.players and all(player.is_eliminated() or player.is_winner() for player in self.players):
            if any(player.is_winner() for player in self.players):
                self.save_screen_to_disk(screen, "victory.png")
                self.switch_to_endgame(VICTORY)
            else:
                self.save_screen_to_disk(screen, "gameover.png")
                self.switch_to_endgame(GAMEOVER)

    def merge_players_lists(
        self,
        webcam_frame: cv2.UMat,
        players: list[Player],
        visible_players: list[Player],
        allow_registration: bool,
        allow_faceless: bool,
        settings: GameSettings,
        crop_info: pygame.Rect,
    ) -> list[Player]:

        for p in players:
            p.set_visible(False)

        for new_p in visible_players:
            # Check if the player is already in the list using track ID from ByteTrack model
            # If not, create a new player object
            p = next((p for p in players if p.get_id() == new_p.get_id()), None)

            if p is not None:
                p.set_visible(True)

            # Capture once face if player is known
            if p is not None and p.get_face() is None:
                face = self.face_extractor.extract_face(webcam_frame, new_p.get_coords(), new_p.get_id())
                if face is not None:
                    p.set_face(face)
            if p is not None and not p.is_eliminated() and new_p.is_eliminated():
                # Update face on elimination
                face = self.face_extractor.extract_face(webcam_frame, new_p.get_coords(), new_p.get_id())
                if face is not None:
                    p.set_face(face)

            # Update player position, or create a new player
            if p is not None:
                p.set_coords(new_p.get_coords())
            else:
                if allow_registration:
                    face = self.face_extractor.extract_face(webcam_frame, new_p.get_coords(), new_p.get_id())
                    if face is not None:
                        new_p.set_face(face)
                    # Add new player only if he is facing the camera
                    if allow_faceless or face is not None:
                        # Check if the player bounding box intersects with the starting area
                        player_rect = GameCamera.convert_nn_to_screen_coord(new_p.get_rect(), webcam_frame, crop_info)
                        if GameCamera.intersect(player_rect, settings.get_gameplay_areas()["start"]):
                            players.append(new_p)
        return players

    def load_model(self):
        # Use the same shared neural network loading logic as setup mode
        from .run import load_neural_network
        
        self.tracker = load_neural_network(self.model)
        
        if self.tracker is None:
            logger.error("No tracker could be loaded - application cannot continue")
            self._init_done = False
            return

        logger.debug("Loading face extractor")
        self.face_extractor = FaceExtractor()
        
        # Log CUDA status
        if is_cuda_opencv_available():
            logger.info("🚀 CUDA OpenCV enabled - GPU acceleration active")
        else:
            logger.info("ℹ️ Using CPU-only OpenCV processing")

        logger.info("Model loading complete")
        self._init_done = True

    def save_screen_to_disk(self, screen: pygame.Surface, filename: str) -> None:
        try:
            pygame.image.save(screen, "pictures/screenshot_" + filename, "PNG")
            logger.info(f"Screenshot saved as {filename}")
        except pygame.error as e:
            logger.exception("Error saving screenshot")

    def loading_screen(self, screen: pygame.Surface) -> None:
        clock = pygame.time.Clock()

        # Add loading screen picture during intro sound
        loading_screen_img = pygame.image.load(ROOT + "/media/loading_screen.webp")
        loading_screen_img = pygame.transform.scale(
            loading_screen_img, (self.game_screen.get_desktop_width(), self.game_screen.get_desktop_height() - 200)
        )

        # Load logo image
        logo_img = pygame.image.load(ROOT + "/media/logo.png")
        logo_img = pygame.transform.scale(logo_img, (400, 200))  # Adjust size as needed
        logo_img.set_colorkey((0, 0, 0))

        # Animation parameters
        logo_x = (self.game_screen.get_desktop_width() - logo_img.get_width()) // 2
        logo_y = self.game_screen.get_desktop_height() - logo_img.get_height()
        alpha = 0
        fade_in = True

        self.intro_sound.play(loops=-1)

        if not self._init_done:
            t: Thread = Thread(target=self.load_model, args=[], daemon=True)
            t.start()

        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.close_loading_screen)

        running = True

        while running:
            running = self.handle_events(screen)

            screen.fill(DARK_GREEN)
            screen.blit(loading_screen_img, (0, 0))

            # Handle logo fade-in and fade-out
            if fade_in:
                alpha += 5
                if alpha >= 255:
                    alpha = 255
                    fade_in = False
            else:
                alpha -= 5
                if alpha <= 0:
                    alpha = 0
                    fade_in = True

            logo_img.set_alpha(alpha)
            screen.blit(logo_img, (logo_x, logo_y))

            if self._init_done:
                self.game_screen.draw_active_buttons(screen)

            _, _ = self.cam.read()
            pygame.display.flip()
            clock.tick()
            logger.debug(f"Camera FPS={round(clock.get_fps(),1)}")

        if not self._init_done and t.is_alive():
            t.join()

        self.save_screen_to_disk(screen, "loading_screen.png")
        self.intro_sound.fadeout(1)

    def handle_events(self, screen: pygame.Surface) -> bool:
        # Handle Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                logger.debug(f"Key pressed: {event.key}")
                if event.key == pygame.K_q:
                    logger.info("Game exit requested by user (Q key)")
                    pygame.quit()
                    from sys import exit
                    exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                return self.game_screen.handle_buttons_click(screen, event)
            elif event.type == pygame.JOYBUTTONDOWN:
                return self.game_screen.handle_buttons(self.joystick)

        # Also check if Q key is currently pressed (alternative method)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_q]:
            logger.info("Game exit requested by user (Q key held)")
            return False

        return True

    def game_main_loop(self, screen: pygame.Surface) -> None:
        """Main game loop for the Squid Game (Green Light Red Light).
        Parameters:
        screen (pygame.Surface): The PyGame full screen object.
        """
        # Game Loop
        running: bool = True
        frame_rate: float = 15.0  # Increased from 10.0 for better responsiveness
        # Create a clock object to manage the frame rate
        clock: pygame.time.Clock = pygame.time.Clock()

        self.switch_to_init()

        while running:
            # Wait for model loading to complete
            if not self._init_done:
                self.loading_screen(screen)
                clock.tick(frame_rate)
                # Handle events even during loading to allow Q key exit
                running = self.handle_events(screen)
                continue
                
            # Check if tracker is available before proceeding
            if self.tracker is None:
                logger.error("Tracker not initialized, cannot continue")
                break
                
            nn_frame, webcam_frame, crop_info = self.cam.read_nn(self.settings, self.tracker.get_max_size())
            if nn_frame is None:
                break

            running = self.handle_events(screen)

            if self.game_state == LOADING:
                self.loading_screen(screen)
                self.switch_to_init()

            # Game Logic
            if self.game_state == INIT:
                self.players = []
                self.game_screen.update(screen, nn_frame, self.game_state, self.players, self.shooter, self.settings)
                pygame.display.flip()
                REGISTRATION_DELAY_S: int = 15
                self.start_registration = time.time()
                while time.time() - self.start_registration < REGISTRATION_DELAY_S:
                    nn_frame, webcam_frame, rect_info = self.cam.read_nn(self.settings, self.tracker.get_max_size())
                    if nn_frame is None:
                        break

                    new_players = self.tracker.process_nn_frame(nn_frame, self.settings)
                    self.players = self.merge_players_lists(
                        nn_frame, [], new_players, True, False, self.settings, rect_info
                    )
                    self.game_screen.update(
                        screen, nn_frame, self.game_state, self.players, self.shooter, self.settings
                    )
                    time_remaining = int(REGISTRATION_DELAY_S - time.time() + self.start_registration)
                    self.game_screen.draw_text(
                        screen,
                        f"{time_remaining}",
                        (screen.get_width() // 2 - 150, screen.get_height() // 2 - 150),
                        WHITE,
                        300,
                    )
                    pygame.display.flip()

                    running = self.handle_events(screen)

                    # Stay there until one player registers
                    if len(self.players) == 0:
                        self.start_registration = time.time()

                    clock.tick(frame_rate)
                    logger.debug(f"Reg FPS={round(clock.get_fps(),1)}")

                self.save_screen_to_disk(screen, "init.png")
                self.switch_to_game()

            elif self.game_state in [GREEN_LIGHT, RED_LIGHT]:
                # Has current light delay elapsed?
                if time.time() - self.last_switch_time > self.delay_s:
                    if self.game_state == GREEN_LIGHT:
                        self.save_screen_to_disk(screen, "green_light.png")
                        self.switch_to_redlight()
                    else:
                        self.save_screen_to_disk(screen, "red_light.png")
                        self.switch_to_greenlight()

                # New player positions
                self.players = self.merge_players_lists(
                    nn_frame,
                    self.players,
                    self.tracker.process_nn_frame(nn_frame, self.settings),
                    False,
                    True,
                    self.settings,
                    crop_info,
                )

                # Update last position while the green light is on
                if self.game_state == GREEN_LIGHT:
                    if not self.no_tracker and self.shooter.is_laser_enabled():
                        self.shooter.set_laser(False)
                    for player in self.players:
                        player.set_last_position(player.get_coords())

                # Check for movements during the red light
                if self.game_state == RED_LIGHT:
                    if time.time() > self.last_switch_time:
                        for player in self.players:
                            if (
                                (player.has_moved(self.settings) or player.has_expired())
                                and not player.is_eliminated()
                                and not player.is_winner()
                            ):
                                player.set_eliminated(True)
                                self.red_sound.stop()
                                self.green_sound.stop()
                                self.eliminate_sound.play()
                                if not self.no_tracker and self.shooter.is_laser_enabled():
                                    self.laser_tracker.target = player.get_target()
                                    self.laser_tracker.start()
                                    start_time = time.time()
                                    KILL_DELAY_S: int = 5
                                    while (
                                        time.time() - start_time < KILL_DELAY_S
                                    ) and not self.laser_tracker.shot_complete():
                                        ret, webcam_frame = self.cam.read()
                                        if ret:
                                            self.laser_tracker.update_frame(webcam_frame)
                                        clock.tick(frame_rate)
                                    self.laser_tracker.stop()
                    else:
                        # Update memory of last position
                        player.set_last_position(player.get_coords())

                # The game state will switch to VICTORY / GAMEOVER when all players are either winners or eliminated.
                self.check_endgame_conditions(crop_info, nn_frame, screen)

            elif self.game_state in [GAMEOVER, VICTORY]:
                # Restart after 10 seconds
                if time.time() - self.last_switch_time > 20:
                    self.switch_to_loading()
                    continue

            self.game_screen.update(screen, nn_frame, self.game_state, self.players, self.shooter, self.settings)

            pygame.display.flip()
            # Limit the frame rate
            clock.tick(frame_rate)

            if random.randint(0, 150) == 0:
                self.save_screen_to_disk(screen, "game.png")
                logger.debug(f"Play FPS={round(clock.get_fps(),1)}")

    def start_game(self) -> None:
        """Start the Squid Game (Green Light Red Light)"""
        # Initialize screen
        screen: pygame.Surface = pygame.display.set_mode(
            (self.game_screen.get_desktop_width(), self.game_screen.get_desktop_height()),
            flags=pygame.FULLSCREEN,
            display=self.game_screen.get_display_idx(),
        )
        pygame.display.set_caption("Squid Games - Green Light, Red Light")

        self.loading_screen(screen)

        # Compute aspect ratio and view port for webcam
        ret, _ = self.cam.read()
        if not ret:
            logger.error("Error: Cannot read from webcam")
            return

        self.game_main_loop(screen)

        # Cleanup
        self.cam.release()
