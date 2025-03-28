from threading import Thread
import pygame
import cv2
import random
import time
import os
from GameScreen import GameScreen
from BasePlayerTracker import BasePlayerTracker
from PlayerTrackerUL import PlayerTrackerUL
from Player import Player
from FaceExtractor import FaceExtractor
from GameCamera import GameCamera
import constants
from LaserShooter import LaserShooter
from LaserTracker import LaserTracker
from GameConfig import GameConfig
import platform


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
    ) -> None:
        self.previous_time: float = time.time()
        self.previous_positions: list = []  # List of bounding boxes (tuples)
        self.tracker: BasePlayerTracker = None  # Initialize later
        self.FAKE: bool = False
        self.face_extractor: FaceExtractor = None  # Initialize later
        self.players: list[Player] = []
        self.green_sound: pygame.mixer.Sound = pygame.mixer.Sound(constants.ROOT + "/media/green_light.mp3")
        # 무궁화 꽃이 피었습니다
        self.red_sound: pygame.mixer.Sound = pygame.mixer.Sound(constants.ROOT + "/media/red_light.mp3")
        self.eliminate_sound: pygame.mixer.Sound = pygame.mixer.Sound(constants.ROOT + "/media/eliminated.mp3")
        self.init_sound: pygame.mixer.Sound = pygame.mixer.Sound(constants.ROOT + "/media/init.mp3")
        self.victory_sound: pygame.mixer.Sound = pygame.mixer.Sound(constants.ROOT + "/media/success.mp3")
        self.gunshot_sound: pygame.mixer.Sound = pygame.mixer.Sound(constants.ROOT + "/media/gunshot.mp3")
        self.game_state: str = constants.INIT
        self.last_switch_time: float = time.time()
        self.delay_s: float = 1.0
        self.game_screen = GameScreen(desktop_size, display_idx)
        self.no_tracker: bool = disable_tracker
        self.shooter: LaserShooter = None
        self.laser_tracker: LaserTracker = None
        self.finish_line_y: float = constants.FINISH_LINE_PERC
        self.joystick: pygame.joystick.JoystickType = joystick
        self.start_registration = time.time()
        self._init_done = False
        self.intro_sound: pygame.mixer.Sound = pygame.mixer.Sound(constants.ROOT + "/media/flute.mp3")
        self.cam: GameCamera = cam
        self.config: GameConfig = GameConfig()
        self.model: str = model
        if not self.no_tracker:
            self.shooter = LaserShooter(ip)
            self.laser_tracker = LaserTracker(self.shooter)

        print(
            f"SquidGame(res={desktop_size} on #{display_idx}, tracker disabled={disable_tracker} (ip={ip}), joystick={self.joystick is not None})"
        )

    def switch_to_init(self) -> bool:
        print("Switch to INIT")
        self.game_state = constants.INIT
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
        self.game_screen.set_active_button(1, self.switch_to_config)
        self.face_extractor.reset_memory()
        if not self.no_tracker:
            self.shooter.set_eyes(False)
            self.shooter.rotate_head(False)
        return True

    def switch_to_redlight(self) -> bool:
        print("Switch to REDLIGHT")
        if not self.no_tracker:
            self.shooter.set_eyes(True)
            self.shooter.rotate_head(False)
        self.last_switch_time = time.time() + constants.GRACE_PERIOD_RED_LIGHT_S
        self.game_state = constants.RED_LIGHT
        self.green_sound.stop()
        self.red_sound.play()
        self.delay_s = random.random() * 6 + constants.MINIMUM_RED_LIGHT_S
        return True

    def switch_to_greenlight(self) -> bool:
        print("Switch to GREENLIGHT")
        if not self.no_tracker:
            self.shooter.set_eyes(False)
            self.shooter.rotate_head(True)
        self.last_switch_time = time.time()
        self.game_state = constants.GREEN_LIGHT
        self.green_sound.play()
        self.red_sound.stop()
        self.delay_s = random.random() * 4 + constants.MINIMUM_GREEN_LIGHT_S
        return True

    def switch_to_config(self) -> bool:
        print("Switch to CONFIG")
        self.game_state = constants.CONFIG
        self.players.clear()
        self.last_switch_time = time.time()
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        self.game_screen.set_click_callback(self.config.config_callback)
        return True

    def switch_to_game(self) -> bool:
        print("Switch to GAME")
        pygame.time.delay(1000)
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        return self.switch_to_greenlight()

    def switch_to_loading(self) -> bool:
        print("Switch to LOADING")
        self.game_state = constants.LOADING
        self.last_switch_time = time.time()
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        return True

    def switch_to_endgame(self, endgame_str: str) -> bool:
        print("Switch to ENDGAME")
        self.game_state = endgame_str
        if endgame_str == constants.VICTORY:
            self.victory_sound.play()
        self.last_switch_time = time.time()
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_loading)
        if not self.no_tracker:
            self.shooter.rotate_head(False)
            self.shooter.set_eyes(False)
        return True

    def close_loading_screen(self) -> bool:
        print("close_loading_screen")
        self.game_state = constants.INIT
        return False

    def check_endgame_conditions(self, frame_height: int, screen: cv2.UMat) -> None:
        """
        Checks each player to see if they have reached the finish line (bottom of bounding box at or above finish_line_y).
        Then, if every player is either a winner or eliminated, switches the game state to VICTORY.
        """
        for player in self.players:
            # Only consider players not already eliminated or marked as winner.
            if not player.is_eliminated() and not player.is_winner():
                x1, y1, x2, y2 = player.get_coords()
                # If the bottom of the player's rectangle is above or equal to the finish line,
                # mark the player as a winner. At least two seconds after last transition.
                if y2 >= self.finish_line_y * frame_height and time.time() - self.last_switch_time > 2:
                    player.set_winner()

        # Update game state
        if self.players and all(player.is_eliminated() or player.is_winner() for player in self.players):
            if any(player.is_winner() for player in self.players):
                self.save_screen_to_disk(screen, "victory.png")
                self.switch_to_endgame(constants.VICTORY)
            else:
                self.save_screen_to_disk(screen, "gameover.png")
                self.switch_to_endgame(constants.GAMEOVER)

    def merge_players_lists(
        self,
        webcam_frame: cv2.UMat,
        players: list[Player],
        visible_players: list[Player],
        allow_registration: bool,
        allow_faceless: bool,
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
                        players.append(new_p)
        return players

    def load_model(self):

        if platform.system() == "Linux":
            from PlayerTrackerHailo import PlayerTrackerHailo

            print(f"Loading HAILO model ({self.model})...")
            # self.tracker = PlayerTrackerHailo("yolov11m.hef")
            if self.model != "":
                self.tracker = PlayerTrackerHailo(self.model)
            else:
                self.tracker = PlayerTrackerHailo()
        else:
            print(f"Loading Ultralytics model ({self.model})...")
            if self.model != "":
                self.tracker = PlayerTrackerUL(self.model)
            else:
                self.tracker = PlayerTrackerUL()

        print("Loading face extractor")
        self.face_extractor = FaceExtractor()
        print("Opening webcam...")

        ret, _ = self.cam.read()
        while not ret:
            print("Failure to acquire webcam stream")
            ret, _ = self.cam.read()
            time.sleep(0.1)
        print("load_model complete")

        self._init_done = True

    def save_screen_to_disk(self, screen: pygame.Surface, filename: str) -> None:
        pygame.image.save(screen, "screenshot_" + filename, "PNG")

    def loading_screen(self, screen: pygame.Surface) -> None:
        clock = pygame.time.Clock()

        # Add loading screen picture during intro sound
        loading_screen_img = pygame.image.load(constants.ROOT + "/media/loading_screen.webp")
        loading_screen_img = pygame.transform.scale(
            loading_screen_img, (self.game_screen.get_desktop_width(), self.game_screen.get_desktop_height() - 200)
        )

        # Load logo image
        logo_img = pygame.image.load(constants.ROOT + "/media/logo.png")
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

            screen.fill(constants.DARK_GREEN)
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
            print(f"Camera FPS={round(clock.get_fps(),1)}")

        if not self._init_done and t.is_alive():
            t.join()

        self.save_screen_to_disk(screen, "loading_screen.png")
        self.intro_sound.fadeout(1)

    def handle_events(self, screen: pygame.Surface) -> bool:
        # Handle Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                return self.game_screen.handle_buttons_click(screen, event)
            elif event.type == pygame.JOYBUTTONDOWN:
                return self.game_screen.handle_buttons(self.joystick)

        return True

    def game_main_loop(self, screen: pygame.Surface) -> None:
        """Main game loop for the Squid Game (Green Light Red Light).
        Parameters:
        screen (pygame.Surface): The PyGame full screen object.
        """
        # Game Loop
        running: bool = True
        frame_rate: float = 10.0
        # Create a clock object to manage the frame rate
        clock: pygame.time.Clock = pygame.time.Clock()

        self.switch_to_init()

        while running:
            ret, webcam_frame = self.cam.read()
            if not ret:
                break

            running = self.handle_events(screen)

            # Initial config (exposure, exclusion zone, finish line)
            if self.game_state == constants.CONFIG:
                c_running = True
                while c_running:
                    ret, webcam_frame = self.cam.read()
                    if not ret:
                        break
                    self.game_screen.update_config(screen, webcam_frame, self.shooter, game_conf=self.config)
                    c_running = self.handle_events(screen)
                    pygame.display.flip()
                    clock.tick(frame_rate)
                self.switch_to_init()

            if self.game_state == constants.LOADING:
                self.loading_screen(screen)
                self.switch_to_init()

            # Game Logic
            if self.game_state == constants.INIT:
                self.players = []
                self.game_screen.update(
                    screen, webcam_frame, self.game_state, self.players, self.shooter, self.finish_line_y
                )
                pygame.display.flip()
                REGISTRATION_DELAY_S: int = 15
                self.start_registration = time.time()
                while time.time() - self.start_registration < REGISTRATION_DELAY_S:
                    ret, webcam_frame = self.cam.read()
                    if not ret:
                        break

                    new_players = self.tracker.process_frame(webcam_frame)
                    self.players = self.merge_players_lists(webcam_frame, [], new_players, True, False)
                    self.game_screen.update(
                        screen, webcam_frame, self.game_state, self.players, self.shooter, self.finish_line_y
                    )
                    time_remaining = int(REGISTRATION_DELAY_S - time.time() + self.start_registration)
                    self.game_screen.draw_text(
                        screen,
                        f"{time_remaining}",
                        (screen.get_width() // 2 - 150, screen.get_height() // 2 - 150),
                        constants.WHITE,
                        300,
                    )
                    pygame.display.flip()

                    running = self.handle_events(screen)

                    # Stay there until one player registers
                    if len(self.players) == 0:
                        self.start_registration = time.time()

                    clock.tick(frame_rate)
                    print(f"Reg FPS={round(clock.get_fps(),1)}")

                self.save_screen_to_disk(screen, "init.png")
                # User may have switched mode
                if self.game_state != constants.CONFIG:
                    self.switch_to_game()

            elif self.game_state in [constants.GREEN_LIGHT, constants.RED_LIGHT]:
                # Has current light delay elapsed?
                if time.time() - self.last_switch_time > self.delay_s:
                    if self.game_state == constants.GREEN_LIGHT:
                        self.save_screen_to_disk(screen, "green_light.png")
                        self.switch_to_redlight()
                    else:
                        self.save_screen_to_disk(screen, "red_light.png")
                        self.switch_to_greenlight()

                # New player positions
                self.players = self.merge_players_lists(
                    webcam_frame, self.players, self.tracker.process_frame(webcam_frame), False, True
                )

                # Update last position while the green light is on
                if self.game_state == constants.GREEN_LIGHT:
                    if not self.no_tracker and self.shooter.is_laser_enabled():
                        self.shooter.set_laser(False)
                    for player in self.players:
                        player.set_last_position(player.get_coords())

                # Check for movements during the red light
                if self.game_state == constants.RED_LIGHT:
                    if time.time() > self.last_switch_time:
                        for player in self.players:
                            if (
                                (player.has_moved() or player.has_expired())
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
                h, _, _ = webcam_frame.shape
                self.check_endgame_conditions(h, screen)

            elif self.game_state in [constants.GAMEOVER, constants.VICTORY]:
                # Restart after 10 seconds
                if time.time() - self.last_switch_time > 20:
                    self.switch_to_loading()
                    continue

            self.game_screen.update(
                screen, webcam_frame, self.game_state, self.players, self.shooter, self.finish_line_y
            )

            pygame.display.flip()
            # Limit the frame rate
            clock.tick(frame_rate)
            print(f"Play FPS={round(clock.get_fps(),1)}")

            if random.randint(0, 100) == 0:
                self.save_screen_to_disk(screen, "game.png")

    def start_game(self) -> None:
        """Start the Squid Game (Green Light Red Light)"""
        # Initialize screen
        screen: pygame.Surface = pygame.display.set_mode(
            (self.game_screen.get_desktop_width(), self.game_screen.get_desktop_width()),
            flags=pygame.FULLSCREEN,
            display=self.game_screen.get_display_idx(),
        )
        pygame.display.set_caption("Squid Games - Green Light, Red Light")

        self.loading_screen(screen)

        # Compute aspect ratio and view port for webcam
        ret, frame = self.cam.read()
        if not ret:
            print("Error: Cannot read from webcam")
            return

        self.game_main_loop(screen)

        # Cleanup
        self.cam.release()

    @staticmethod
    def get_desktop(preferred_monitor=0) -> (tuple[int, int], int):
        num = 0
        for size in pygame.display.get_desktop_sizes():
            if num == preferred_monitor:
                return (size, preferred_monitor)
            num += 1
        return (pygame.display.get_desktop_sizes()[0], 0)


def command_line_args() -> any:
    import argparse

    parser = argparse.ArgumentParser("SquidGame.py")
    parser.add_argument(
        "-m", "--monitor", help="0-based index of the monitor", dest="monitor", type=int, default=-1, required=False
    )
    parser.add_argument(
        "-w", "--webcam", help="0-based index of the webcam", dest="webcam", type=int, default=-1, required=False
    )
    parser.add_argument(
        "-t",
        "--tracker",
        help="enable or disable the esp32 laser",
        dest="tracker",
        type=bool,
        default=False,
        required=False,
    )
    parser.add_argument(
        "-i",
        "--tracker-ip",
        help="sets the esp32 tracker IP address",
        dest="ip",
        type=str,
        default="192.168.45.50",
        required=False,
    )
    parser.add_argument(
        "-j",
        "--joystick",
        help="sets the joystick index",
        dest="joystick",
        type=int,
        default=-1,
        required=False,
    )
    parser.add_argument(
        "-md",
        "--model",
        help="specify model for player recognition",
        dest="model",
        type=str,
        default="",
        required=False,
    )
    return parser.parse_args()


if __name__ == "__main__":
    if platform.system() != "Linux":
        import ctypes

        ctypes.windll.user32.SetProcessDPIAware()
        # Disable hardware acceleration for webcam on Windows
        os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

    pygame.init()

    args = command_line_args()
    size, monitor = SquidGame.get_desktop(args.monitor)
    joystick = None
    if args.joystick != -1:
        joystick = pygame.joystick.Joystick(args.joystick)
        print(f"Using joystick: {joystick.get_name()}")
    else:
        print("Joysticks:")
        for idx in range(0, pygame.joystick.get_count()):
            print(f"\t{idx}:{pygame.joystick.Joystick(idx).get_name()}")
        print("-")

    cam = GameCamera(args.webcam)

    if not cam.valid:
        print("No compatible webcam found")
        exit(1)

    if args.model != "" and not os.path.exists(args.model):
        print("Invalid model file")
        exit(1)

    game = SquidGame(
        disable_tracker=not args.tracker,
        desktop_size=size,
        display_idx=monitor,
        ip=args.ip,
        joystick=joystick,
        cam=cam,
        model=args.model,
    )

    while True:
        try:
            game.start_game()
        except Exception as e:
            print("Exception", e)
            raise e
