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
    def __init__(self, disable_tracker: bool, desktop_size: tuple[int, int], display_idx: int, ip: str) -> None:
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
        self.game_state: str = constants.INIT
        self.last_switch_time: float = time.time()
        self.delay_s: int = random.randint(2, 5)
        self.game_screen = GameScreen(desktop_size, display_idx)
        self.cap: cv2.VideoCapture = None  # Initialize later
        self.no_tracker: bool = disable_tracker
        self.shooter: LaserShooter = None
        self.laser_tracker: LaserTracker = None

        if not self.no_tracker:
            self.shooter = LaserShooter(ip)
            self.laser_tracker = LaserTracker(self.shooter)

        print(f"SquidGame(res={desktop_size} on #{display_idx}, tracker disabled={disable_tracker}, ip={ip})")

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

        click_img = pygame.image.load(constants.ROOT + "/media/mouse_click.gif")

        # Animation parameters
        logo_x = (self.game_screen.get_desktop_width() - logo_img.get_width()) // 2
        logo_y = self.game_screen.get_desktop_width() - logo_img.get_height()
        alpha = 0
        fade_in = True

        intro_sound.play(loops=-1)

        t: Thread = Thread(target=self.load_model, args=[webcam_idx])
        t.start()

        running = True
        while running:
            screen.fill(constants.DARK_GREEN)
            screen.blit(loading_screen_img, (0, 0))

            for event in pygame.event.get():
                if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                    running = False

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
                screen.blit(
                    click_img,
                    (
                        self.game_screen.get_desktop_width() - click_img.get_width(),
                        self.game_screen.get_desktop_height() - click_img.get_height(),
                    ),
                )

            pygame.display.flip()
            pygame.time.wait(50)

        if t.is_alive():
            t.join()

        intro_sound.fadeout(1)

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
        MIN_RED_LIGHT_DELAY_S: float = 0.8

        while running:
            screen.fill(constants.SALMON)

            ret, frame = self.cap.read()
            if not ret:
                break

            # Handle Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.game_screen.is_button_click(event):
                        self.game_state = constants.INIT  # Reset the game
                        self.players.clear()
                        self.last_switch_time = time.time()

            # Game Logic
            if self.game_state == constants.INIT:
                self.green_sound.stop()
                self.red_sound.stop()
                self.eliminate_sound.stop()
                self.players = []
                self.game_screen.update_screen(screen, frame, self.game_state, self.players, self.shooter)
                pygame.display.flip()
                REGISTRATION_DELAY_S: int = 15
                start_registration = time.time()
                while time.time() - start_registration < REGISTRATION_DELAY_S:
                    ret, frame = self.cap.read()
                    if not ret:
                        break

                    new_players = self.tracker.process_frame(frame)
                    self.players = self.merge_players_lists(frame, [], new_players, True)
                    self.game_screen.update_screen(screen, frame, self.game_state, self.players, self.shooter)
                    time_remaining = int(REGISTRATION_DELAY_S - time.time() + start_registration)
                    self.game_screen.draw_text(
                        screen,
                        f"{time_remaining}",
                        (screen.get_width() // 2, screen.get_height() // 2),
                        constants.WHITE,
                        200,
                    )
                    pygame.display.flip()

                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                            return

                    clock.tick(10)

                self.game_state = constants.GREEN_LIGHT
                self.green_sound.play()
                pygame.time.delay(1000)
                self.last_switch_time = time.time()

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
                    self.delay_s = random.randint(2, 10) / 2

                # New player positions
                self.players = self.merge_players_lists(frame, self.players, self.tracker.process_frame(frame), False)

                # Update last position while the green light is on
                if self.game_state == constants.GREEN_LIGHT:
                    if not self.no_tracker:
                        self.shooter.set_laser(False)
                    for player in self.players:
                        player.set_last_position(player.get_coords())

                # Check for movements during the red light
                if (
                    self.game_state == constants.RED_LIGHT
                    and time.time() - self.last_switch_time > MIN_RED_LIGHT_DELAY_S
                ):
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

            elif self.game_state in [constants.GAMEOVER, constants.VICTORY]:
                # Restart after 10 seconds
                if time.time() - self.last_switch_time > 20:
                    self.game_state = constants.INIT
                    self.players.clear()
                    self.last_switch_time = time.time()
                    continue

            # Check for victory
            # Verifica se ci sono ancora giocatori rimasti
            if (
                len([p for p in self.players if p.is_eliminated()]) == len(self.players)
                and len(self.players) > 0
                and self.game_state != constants.GAMEOVER
            ):
                self.game_state = constants.GAMEOVER
                self.last_switch_time = time.time()

            self.game_screen.update_screen(screen, frame, self.game_state, self.players, self.shooter)

            pygame.display.flip()
            # Limit the frame rate
            clock.tick(frame_rate)

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

        self.game_screen.setup_ratios(frame)
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
    game = SquidGame(disable_tracker=not args.tracker, desktop_size=size, display_idx=monitor, ip=args.ip)
    index: int = Camera.getCameraIndex(args.webcam)
    if index == -1:
        print("No compatible webcam found")
        exit(1)
    game.start_game(index)
