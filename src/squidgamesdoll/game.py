from threading import Thread
import pygame
import cv2
import numpy as np
import random
import time
import os
from GameScreen import GameScreen
from players_tracker import PlayerTracker, Player
from face_extractor import FaceExtractor
from camera import Camera
import constants
from LaserShooter import LaserShooter


class SquidGame:
    def __init__(self) -> None:
        pygame.init()

        self.previous_time: float = time.time()
        self.previous_positions: list = []  # List of bounding boxes (tuples)
        self.tracker: PlayerTracker = None  # Initialize later
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
        self.game_screen = GameScreen()
        self.cap: cv2.VideoCapture = None  # Initialize later
        self.shooter: LaserShooter = LaserShooter(constants.ESP32_IP)

    def merge_players_lists(
        self, webcam_frame: cv2.UMat, players: list[Player], new_players: list[Player]
    ) -> list[Player]:
        for new_p in new_players:
            # Check if the player is already in the list
            p = next((p for p in players if p.id == new_p.id), None)
            # Capture face if player is known
            if p is not None and p.get_face() is None:
                face = self.face_extractor.extract_face(webcam_frame, new_p.get_coords())
                if face is not None:
                    p.set_face(face)
            if p is not None and not p.eliminated and new_p.eliminated:
                # Update face on elimination
                face = self.face_extractor.extract_face(webcam_frame, new_p.get_coords())
                if face is not None:
                    p.set_face(face)

            # Update player position, or create a new player
            if p is not None:
                p.set_coords(new_p.get_coords())
            else:
                players.append(new_p)
        return players

    def load_model(self, webcam_idx: int):
        self.tracker = PlayerTracker()
        self.face_extractor = FaceExtractor()
        # Use DSHOW on Windows to avoid slow startup
        self.cap: cv2.VideoCapture = cv2.VideoCapture(webcam_idx, cv2.CAP_DSHOW)

        # Configure webcam stream settings
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
        self.cap.set(cv2.CAP_PROP_FPS, 15.0)

        ret, _ = self.cap.read()
        while not ret:
            ret, _ = self.cap.read()
            time.sleep(0.1)
        print("load_model complete")

    def loading_screen(self, screen: pygame.Surface, webcam_idx: int) -> None:
        # Load sounds
        intro_sound: pygame.mixer.Sound = pygame.mixer.Sound(constants.ROOT + "/media/mingle.mp3")

        # Add loading screen picture during intro sound
        loading_screen_img = pygame.image.load(constants.ROOT + "/media/loading_screen.webp")
        loading_screen_img = pygame.transform.scale(loading_screen_img, (constants.WIDTH, constants.HEIGHT - 200))

        # Load logo image
        logo_img = pygame.image.load(constants.ROOT + "/media/logo.png")
        logo_img = pygame.transform.scale(logo_img, (400, 200))  # Adjust size as needed
        logo_img.set_colorkey((0, 0, 0))

        click_img = pygame.image.load(constants.ROOT + "/media/mouse_click.gif")

        # Animation parameters
        logo_x = (constants.WIDTH - logo_img.get_width()) // 2
        logo_y = constants.HEIGHT - logo_img.get_height()
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
                    click_img, (constants.WIDTH - click_img.get_width(), constants.HEIGHT - click_img.get_height())
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
                self.players = self.tracker.process_frame(frame)
                self.game_screen.update_screen(screen, frame, self.game_state, self.players, self.shooter)

                while len(self.players) < 1:
                    ret, frame = self.cap.read()
                    if not ret:
                        break

                    self.players = self.tracker.process_frame(frame)
                    self.game_screen.update_screen(screen, frame, self.game_state, self.players, self.shooter)

                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                            return
                    clock.tick(frame_rate)

                self.game_state = constants.GREEN_LIGHT
                self.green_sound.play()

            elif self.game_state in [constants.GREEN_LIGHT, constants.RED_LIGHT]:
                # Switch phase randomly (1-5 seconds)
                if time.time() - self.last_switch_time > self.delay_s:
                    green_light = not green_light
                    self.last_switch_time = time.time()
                    self.game_state = constants.GREEN_LIGHT if green_light else constants.RED_LIGHT
                    (self.red_sound if green_light else self.green_sound).stop()
                    (self.green_sound if green_light else self.red_sound).play()
                    self.delay_s = random.randint(2, 10) / 2

                # New player positions (simulating new detections)
                self.players = self.merge_players_lists(frame, self.players, self.tracker.process_frame(frame))

                # Update last position while the green light is on
                if self.game_state == constants.GREEN_LIGHT:
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
                            self.eliminate_sound.play()

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
        screen: pygame.Surface = pygame.display.set_mode((constants.WIDTH, constants.HEIGHT), pygame.RESIZABLE)
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


if __name__ == "__main__":
    # Disable hardware acceleration for webcam on Windows
    os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

    game = SquidGame()
    index: int = Camera.getCameraIndex()
    if index == -1:
        print("No compatible webcam found")
        exit(1)
    game.start_game(index)
