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
from camera import Camera
import constants
from LaserShooter import LaserShooter
from LaserTracker import LaserTracker
import platform


class SquidGame:
    def __init__(
        self,
        disable_tracker: bool,
        desktop_size: tuple[int, int],
        display_idx: int,
        ip: str,
        joystick: pygame.joystick.JoystickType,
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
        self.delay_s: int = random.randint(2, 5)
        self.game_screen = GameScreen(desktop_size, display_idx)
        self.cap: cv2.VideoCapture = None  # Initialize later
        self.no_tracker: bool = disable_tracker
        self.shooter: LaserShooter = None
        self.laser_tracker: LaserTracker = None
        self.finish_line_y: float = constants.FINISH_LINE_PERC
        self.joystick: pygame.joystick.JoystickType = joystick
        self.start_registration = time.time()

        if not self.no_tracker:
            self.shooter = LaserShooter(ip)
            self.laser_tracker = LaserTracker(self.shooter)

        print(
            f"SquidGame(res={desktop_size} on #{display_idx}, tracker disabled={disable_tracker} (ip={ip}), joystick={self.joystick is not None})"
        )

    def switch_to_init(self) -> bool:
        self.game_state = constants.INIT
        self.players.clear()
        self.last_switch_time = time.time()
        self.green_sound.stop()
        self.red_sound.stop()
        self.eliminate_sound.stop()
        self.init_sound.play()
        self.start_registration = time.time()
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        return True

    def switch_to_config(self) -> bool:
        self.game_state = constants.CONFIG
        self.players.clear()
        self.last_switch_time = time.time()
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        return True

    def switch_to_game(self) -> bool:
        self.game_state = constants.GREEN_LIGHT
        self.green_sound.play()
        pygame.time.delay(1000)
        self.last_switch_time = time.time()
        self.delay_s = random.randint(2, 6) / 2
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        return True

    def switch_to_endgame(self, endgame_str: str) -> bool:
        self.game_state = endgame_str
        if endgame_str == constants.VICTORY:
            self.victory_sound.play()
        self.last_switch_time = time.time()
        self.game_screen.reset_active_buttons()
        self.game_screen.set_active_button(0, self.switch_to_init)
        return True

    def close_loading_screen(self) -> bool:
        return False

    def check_endgame_conditions(self, frame_height: int) -> None:
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
                self.switch_to_endgame(constants.VICTORY)
            else:
                self.switch_to_endgame(constants.GAMEOVER)

    def merge_players_lists(
        self, webcam_frame: cv2.UMat, players: list[Player], visible_players: list[Player], allow_registration: bool
    ) -> list[Player]:

        for p in players:
            p.set_visible(False)

        for new_p in visible_players:
            # Check if the player is already in the list
            p = next((p for p in players if p.get_id() == new_p.get_id()), None)

            if p is not None:
                p.set_visible(True)

            # Capture once face if player is known
            if p is not None and p.get_face() is None:
                face = self.face_extractor.extract_face(webcam_frame, new_p.get_coords())
                if face is not None:
                    p.set_face(face)
            if p is not None and not p.is_eliminated() and new_p.is_eliminated():
                # Update face on elimination
                face = self.face_extractor.extract_face(webcam_frame, new_p.get_coords())
                if face is not None:
                    p.set_face(face)

            # Update player position, or create a new player
            if p is not None:
                p.set_coords(new_p.get_coords())
            else:
                if allow_registration:
                    face = self.face_extractor.extract_face(webcam_frame, new_p.get_coords())
                    if face is not None:
                        new_p.set_face(face)
                    players.append(new_p)
        return players

    def load_model(self, webcam_idx: int):

        if platform.system() == "Linux":
            from PlayerTrackerHailo import PlayerTrackerHailo

            print("Loading HAILO model...")
            self.tracker = PlayerTrackerHailo("yolov11m.hef")
        else:
            print("Loading Ultralytics model...")
            self.tracker = PlayerTrackerUL()

        print("Loading face extractor")
        self.face_extractor = FaceExtractor()
        print("Opening webcam...")
        # Use DSHOW on Windows to avoid slow startup
        self.cap: cv2.VideoCapture = cv2.VideoCapture(webcam_idx)  # , cv2.CAP_DSHOW)

        # Configure webcam stream settings
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
        self.cap.set(cv2.CAP_PROP_FPS, 15.0)

        ret, _ = self.cap.read()
        while not ret:
            print("Failure to acquire webcam stream")
            ret, _ = self.cap.read()
            time.sleep(0.1)
        print("load_model complete")

    def loading_screen(self, screen: pygame.Surface, webcam_idx: int) -> None:
        # Load sounds
        intro_sound: pygame.mixer.Sound = pygame.mixer.Sound(constants.ROOT + "/media/flute.mp3")

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

        intro_sound.play(loops=-1)

        t: Thread = Thread(target=self.load_model, args=[webcam_idx])
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

            if not t.is_alive():
                self.game_screen.draw_active_buttons(screen)

            pygame.display.flip()
            pygame.time.wait(50)

        if t.is_alive():
            t.join()

        intro_sound.fadeout(1)

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
        cap (cv2.VideoCapture): The video capture object from the webcam.
        screen (pygame.Surface): The PyGame full screen object.
        view_port (tuple): The view port for the webcam (width, height).
        x_ratio (float): The aspect ratio for the x-axis between webcam frame and viewport.
        y_ratio (float): The aspect ratio for the y-axis between webcam frame and viewport.
        """
        # Game Loop
        green_light: bool = True
        running: bool = True
        frame_rate: float = 15.0
        # Create a clock object to manage the frame rate
        clock: pygame.time.Clock = pygame.time.Clock()
        MIN_RED_LIGHT_DELAY_S: float = 0.7

        self.switch_to_init()

        while running:
            ret, frame = self.cap.read()
            if not ret:
                break

            running = self.handle_events(screen)

            # Initial config (exposure, exclusion zone, finish line)
            if self.game_state == constants.CONFIG:
                while running:
                    ret, frame = self.cap.read()
                    if not ret:
                        break
                    self.game_screen.update_config(screen, frame, self.shooter)
                    running = self.handle_events(screen)
                    pygame.display.flip()
                    clock.tick(frame_rate)

            # Game Logic
            if self.game_state == constants.INIT:
                self.players = []
                self.game_screen.update(screen, frame, self.game_state, self.players, self.shooter, self.finish_line_y)
                pygame.display.flip()
                REGISTRATION_DELAY_S: int = 15
                self.start_registration = time.time()
                while time.time() - self.start_registration < REGISTRATION_DELAY_S:
                    ret, frame = self.cap.read()
                    if not ret:
                        break

                    new_players = self.tracker.process_frame(frame)
                    self.players = self.merge_players_lists(frame, [], new_players, True)
                    self.game_screen.update(
                        screen, frame, self.game_state, self.players, self.shooter, self.finish_line_y
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

                self.switch_to_game()

            elif self.game_state in [constants.GREEN_LIGHT, constants.RED_LIGHT]:
                # Switch phase randomly (1-5 seconds)
                if time.time() - self.last_switch_time > self.delay_s:
                    green_light = not green_light
                    if not self.no_tracker:
                        self.shooter.rotate_head(green_light)
                    self.last_switch_time = time.time()
                    self.game_state = constants.GREEN_LIGHT if green_light else constants.RED_LIGHT
                    (self.red_sound if green_light else self.green_sound).stop()
                    (self.green_sound if green_light else self.red_sound).play()
                    self.delay_s = random.randint(2, 6) / 2
                    if self.game_state == constants.RED_LIGHT:
                        self.delay_s += 2

                # New player positions
                self.players = self.merge_players_lists(frame, self.players, self.tracker.process_frame(frame), False)

                # Update last position while the green light is on
                if self.game_state == constants.GREEN_LIGHT:
                    if not self.no_tracker:
                        self.shooter.set_laser(False)
                    for player in self.players:
                        player.set_last_position(player.get_coords())

                # Check for movements during the red light
                if self.game_state == constants.RED_LIGHT:
                    if time.time() - self.last_switch_time > MIN_RED_LIGHT_DELAY_S:
                        for player in self.players:
                            if player.has_moved() and not player.is_eliminated():
                                player.set_eliminated(True)
                                self.red_sound.stop()
                                self.green_sound.stop()
                                self.eliminate_sound.play()
                                if not self.no_tracker:
                                    self.laser_tracker.target = player.get_target()
                                    self.laser_tracker.start()
                                    start_time = time.time()
                                    KILL_DELAY_S: int = 5
                                    while (
                                        time.time() - start_time < KILL_DELAY_S
                                    ) and not self.laser_tracker.shot_complete():
                                        ret, frame = self.cap.read()
                                        if ret:
                                            self.laser_tracker.update_frame(frame)
                                        clock.tick(frame_rate)
                                    self.laser_tracker.stop()
                    else:
                        # Grace period
                        player.set_last_position(player.get_coords())

                # The game state will switch to VICTORY / GAMEOVER when all players are either winners or eliminated.
                h, _, _ = frame.shape
                self.check_endgame_conditions(h)

            elif self.game_state in [constants.GAMEOVER, constants.VICTORY]:
                # Restart after 10 seconds
                if time.time() - self.last_switch_time > 20:
                    self.switch_to_init()
                    continue

            self.game_screen.update(screen, frame, self.game_state, self.players, self.shooter, self.finish_line_y)

            pygame.display.flip()
            # Limit the frame rate
            clock.tick(frame_rate)
            print("FPS=", clock.get_fps())

    def start_game(self, webcam_idx: int = 0) -> None:
        """Start the Squid Game (Green Light Red Light) with the given webcam index.
        Parameters:
            webcam_idx (int): The index of the webcam to use.
        """
        # Initialize screen
        screen: pygame.Surface = pygame.display.set_mode(
            (self.game_screen.get_desktop_width(), self.game_screen.get_desktop_width()),
            flags=pygame.FULLSCREEN,
            display=self.game_screen.get_display_idx(),
        )
        pygame.display.set_caption("Squid Games - Green Light, Red Light")

        self.loading_screen(screen, webcam_idx)

        self.game_state = constants.INIT
        self.players = []  # Reset players list

        # Timing for Red/Green Light
        self.last_switch_time = time.time()

        # Compute aspect ratio and view port for webcam
        ret, frame = self.cap.read()
        if not ret:
            print("Error: Cannot read from webcam")
            return

        self.game_main_loop(screen)

        # Cleanup
        self.cap.release()

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
    game = SquidGame(
        disable_tracker=not args.tracker, desktop_size=size, display_idx=monitor, ip=args.ip, joystick=joystick
    )
    index: int = Camera.getCameraIndex(args.webcam)
    if index == -1:
        print("No compatible webcam found")
        exit(1)

    while True:
        try:
            game.start_game(index)
        except Exception as e:
            print("Exception", e)
