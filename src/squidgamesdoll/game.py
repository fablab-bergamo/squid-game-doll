from threading import Thread
import pygame
import cv2
import numpy as np
import random
import time
import os
from display_players import GameScreen
from players_tracker import PlayerTracker, Player
from face_extractor import FaceExtractor
from camera import Camera
from img_processing import opencv_to_pygame


class SquidGame:
    # Color Constants
    GREEN: tuple[int, int, int] = (0, 255, 0)
    RED: tuple[int, int, int] = (255, 0, 0)
    WHITE: tuple[int, int, int] = (255, 255, 255)
    BLACK: tuple[int, int, int] = (0, 0, 0)
    YELLOW: tuple[int, int, int] = (255, 255, 0)
    DARK_GREEN: tuple[int, int, int] = (3, 122, 118)
    LIGHT_GREEN: tuple[int, int, int] = (36, 159, 156)
    SALMON: tuple[int, int, int] = (244, 71, 134)
    PINK: tuple[int, int, int] = (237, 27, 118)

    # Screen Dimensions
    WIDTH: int = 1600
    HEIGHT: int = 1200

    # Font Color
    FONT_COLOR: tuple[int, int, int] = RED

    # Game States
    INIT: str = "INIT"
    GREEN_LIGHT: str = "GREEN_LIGHT"
    RED_LIGHT: str = "RED_LIGHT"
    VICTORY: str = "VICTORY"
    GAMEOVER: str = "GAME OVER"

    # Button Properties
    BUTTON_COLOR: tuple[int, int, int] = (255, 0, 0)  # Red like Squid Game theme
    BUTTON_HOVER_COLOR: tuple[int, int, int] = (200, 0, 0)
    BUTTON_TEXT_COLOR: tuple[int, int, int] = (0, 0, 0)  # Black text
    BUTTON_RECT: pygame.Rect = pygame.Rect(1350, 1100, 200, 50)  # Position and size

    def __init__(self) -> None:
        pygame.init()

        self.ROOT: str = os.path.dirname(__file__)

        self.FONT: pygame.font.Font = pygame.font.Font(self.ROOT + "/media/SpaceGrotesk-Regular.ttf", 36)
        self.FONT_FINE: pygame.font.Font = pygame.font.Font(self.ROOT + "/media/SpaceGrotesk-Regular.ttf", 85)

        self.previous_time: float = time.time()
        self.previous_positions: list = []  # List of bounding boxes (tuples)
        self.tracker: PlayerTracker = None  # Initialize later
        self.FAKE: bool = False
        self.face_extractor: FaceExtractor = None  # Initialize later
        self.players: list[Player] = []
        self.green_sound: pygame.mixer.Sound = pygame.mixer.Sound(self.ROOT + "/media/green_light.mp3")
        # 무궁화 꽃이 피었습니다
        self.red_sound: pygame.mixer.Sound = pygame.mixer.Sound(self.ROOT + "/media/red_light.mp3")
        self.eliminate_sound: pygame.mixer.Sound = pygame.mixer.Sound(self.ROOT + "/media/eliminated.mp3")
        self.game_state: str = self.INIT
        self.last_switch_time: float = time.time()
        self.delay_s: int = random.randint(2, 5)
        self.game_screen = GameScreen()
        self.cap: cv2.VideoCapture = None  # Initialize later

    def draw_overlay(self, screen: pygame.Surface, game_state: str) -> None:
        """Display game status.

        Parameters:
            screen (pygame.Surface): The PyGame screen.
            game_state (str): Current game state.
        """
        text = self.FONT.render(f"Phase: {game_state}", True, self.FONT_COLOR)
        screen.blit(text, (20, 20))

    def convert_player_list(self, players: list[Player]) -> list[dict]:
        # Creiamo un dizionario per mantenere giocatori unici con il loro stato
        risultato: list[dict] = []
        cpt: int = 1
        # Aggiungiamo i giocatori dalla lista attiva/eliminata
        for player in players:
            img = player.get_image()
            if img is None:
                img = self.game_screen.load_player_image(
                    os.path.join(os.path.dirname(__file__), "media/sample_player.jpg")
                )
            risultato.append(
                {
                    "number": cpt,
                    "active": not player.is_eliminated(),
                    "image": img,
                    "rectangle": player.get_rect(),
                    "id": player.id,
                }
            )
            cpt += 1
        return risultato

    def draw_light(self, screen: pygame.Surface, green_light: bool) -> None:
        # Draw the light in the bottom part of the screen
        position: tuple[int, int] = (self.WIDTH // 4, self.HEIGHT // 4 * 3)
        radius: int = min(self.WIDTH // 8, self.HEIGHT // 8) - 4
        if green_light:
            pygame.draw.circle(screen, self.GREEN, position, radius)
        else:
            pygame.draw.circle(screen, self.RED, position, radius)

        pygame.draw.circle(screen, self.BLACK, position, radius, 4)

    def draw_bounding_boxes(
        self,
        frame_surface: pygame.Surface,
        x_ratio: float,
        y_ratio: float,
        players: list[Player],
        add_previous_pos: bool = False,
    ) -> None:
        for player in players:
            color: tuple[int, int, int] = (
                self.RED if player.is_eliminated() else (self.GREEN if not player.has_moved() else self.YELLOW)
            )
            x, y, w, h = player.get_rect()
            # transforms the coordinates from the webcam frame to the pygame frame using the ratios
            x, y, w, h = x / x_ratio, y / y_ratio, w / x_ratio, h / y_ratio
            pygame.draw.rect(frame_surface, color, (x, y, w, h), 3)

            # Draw the last position
            if add_previous_pos and player.get_last_position() is not None and not player.is_eliminated():
                x, y, w, h = player.get_last_rect()
                x, y, w, h = x / x_ratio, y / y_ratio, w / x_ratio, h / y_ratio
                pygame.draw.rect(frame_surface, self.WHITE, (x, y, w, h), 1)

            if player.is_eliminated():
                pygame.draw.line(
                    frame_surface,
                    self.RED,
                    (x, y),
                    (x + w, y + h),
                    5,
                )
                pygame.draw.line(
                    frame_surface,
                    self.RED,
                    (x + w, y),
                    (x, y + h),
                    5,
                )

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
        intro_sound: pygame.mixer.Sound = pygame.mixer.Sound(self.ROOT + "/media/mingle.mp3")

        # Add loading screen picture during intro sound
        loading_screen_img = pygame.image.load(self.ROOT + "/media/loading_screen.webp")
        loading_screen_img = pygame.transform.scale(loading_screen_img, (self.WIDTH, self.HEIGHT - 200))

        # Load logo image
        logo_img = pygame.image.load(self.ROOT + "/media/logo.png")
        logo_img = pygame.transform.scale(logo_img, (400, 200))  # Adjust size as needed
        logo_img.set_colorkey((0, 0, 0))

        click_img = pygame.image.load(self.ROOT + "/media/mouse_click.gif")

        # Animation parameters
        logo_x = (self.WIDTH - logo_img.get_width()) // 2
        logo_y = self.HEIGHT - logo_img.get_height()
        alpha = 0
        fade_in = True

        intro_sound.play(loops=-1)

        t: Thread = Thread(target=self.load_model, args=[webcam_idx])
        t.start()

        running = True
        while running:
            screen.fill(SquidGame.DARK_GREEN)
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
                screen.blit(click_img, (self.WIDTH - click_img.get_width(), self.HEIGHT - click_img.get_height()))

            pygame.display.flip()
            pygame.time.wait(50)

        if t.is_alive():
            t.join()

        intro_sound.fadeout(1)

    def draw_button(self, screen: pygame.Surface) -> None:
        mouse_pos: tuple[int, int] = pygame.mouse.get_pos()
        button_color: tuple[int, int, int] = (
            self.BUTTON_HOVER_COLOR if self.BUTTON_RECT.collidepoint(mouse_pos) else self.BUTTON_COLOR
        )
        pygame.draw.rect(screen, button_color, self.BUTTON_RECT, border_radius=10)
        text = self.FONT.render("Re-init", True, self.BUTTON_TEXT_COLOR)
        text_rect: pygame.Rect = text.get_rect(center=self.BUTTON_RECT.center)
        screen.blit(text, text_rect)

    def game_main_loop(
        self,
        cap: cv2.VideoCapture,
        screen: pygame.Surface,
        view_port: tuple[int, int],
        x_ratio: float,
        y_ratio: float,
    ) -> None:
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
            screen.fill(SquidGame.SALMON)

            ret, frame = self.cap.read()
            if not ret:
                break

            # Convert OpenCV BGR to RGB for PyGame
            frame_surface: pygame.Surface = opencv_to_pygame(frame, view_port)

            # Handle Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.BUTTON_RECT.collidepoint(event.pos):
                        self.game_state = self.INIT  # Reset the game
                        self.players.clear()
                        self.last_switch_time = time.time()

            # Game Logic
            if self.game_state == SquidGame.INIT:
                self.players = self.tracker.process_frame(frame)
                self.draw_overlay(screen, self.game_state)
                text = self.FONT.render("Waiting for players...", True, self.FONT_COLOR)
                screen.blit(text, (self.WIDTH // 2 - 100, self.HEIGHT // 2))
                pygame.display.flip()

                while len(self.players) < 1:
                    ret, frame = self.cap.read()
                    if not ret:
                        break
                    screen.blit(frame_surface, (0, 0))
                    self.players = self.tracker.process_frame(frame)
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                            return
                    clock.tick(frame_rate)

                self.game_state = SquidGame.GREEN_LIGHT
                self.green_sound.play()

            elif self.game_state in [SquidGame.GREEN_LIGHT, SquidGame.RED_LIGHT]:
                # Switch phase randomly (1-5 seconds)
                if time.time() - self.last_switch_time > self.delay_s:
                    green_light = not green_light
                    self.last_switch_time = time.time()
                    self.game_state = SquidGame.GREEN_LIGHT if green_light else SquidGame.RED_LIGHT
                    (self.red_sound if green_light else self.green_sound).stop()
                    (self.green_sound if green_light else self.red_sound).play()
                    self.delay_s = random.randint(2, 10) / 2

                # New player positions (simulating new detections)
                self.players = self.merge_players_lists(frame, self.players, self.tracker.process_frame(frame))

                # Update last position while the green light is on
                if self.game_state == SquidGame.GREEN_LIGHT:
                    for player in self.players:
                        player.set_last_position(player.get_coords())

                # Check for movements during the red light
                if (
                    self.game_state == SquidGame.RED_LIGHT
                    and time.time() - self.last_switch_time > MIN_RED_LIGHT_DELAY_S
                ):
                    for player in self.players:
                        if player.has_moved() and not player.is_eliminated():
                            player.set_eliminated(True)
                            self.eliminate_sound.play()

                # Draw bounding boxes
                self.draw_bounding_boxes(
                    frame_surface,
                    x_ratio,
                    y_ratio,
                    self.players,
                    add_previous_pos=True,
                )

                # Add red / green light
                self.draw_light(screen, green_light)

            elif self.game_state in [SquidGame.GAMEOVER, SquidGame.VICTORY]:
                # Restart after 10 seconds
                if time.time() - self.last_switch_time > 20:
                    self.game_state = SquidGame.INIT
                    self.players.clear()
                    self.last_switch_time = time.time()
                    continue

            # Check for victory
            # Verifica se ci sono ancora giocatori rimasti
            if (
                len([p for p in self.players if p.is_eliminated()]) == len(self.players)
                and len(self.players) > 0
                and self.game_state != SquidGame.GAMEOVER
            ):
                self.game_state = SquidGame.GAMEOVER
                self.last_switch_time = time.time()

            # display players on a new surface on the half right of the screen
            players_surface: pygame.Surface = pygame.Surface((self.WIDTH // 2, self.HEIGHT))
            self.game_screen.display_players(players_surface, self.convert_player_list(self.players), SquidGame.SALMON)

            won = sum([100_000_000 for p in self.players if p.is_eliminated()])
            self.game_screen.display_won(screen, won, self.FONT_FINE)

            # Show webcam feed
            screen.blit(frame_surface, (0, 0))
            # Show players screen
            screen.blit(players_surface, (self.WIDTH // 2, 0))
            self.draw_button(screen)

            if self.game_state == SquidGame.GAMEOVER:
                text = self.FONT_FINE.render("GAME OVER! No vincitori...", True, self.WHITE)
                screen.blit(text, (self.WIDTH // 2 - 400, self.HEIGHT - 350))

            if self.game_state == SquidGame.VICTORY:
                text = self.FONT_FINE.render("VICTORY!", True, self.DARK_GREEN)
                screen.blit(text, (self.WIDTH // 2 - 400, self.HEIGHT - 350))

            pygame.display.flip()
            # Limit the frame rate
            clock.tick(frame_rate)

    def start_game(self, webcam_idx: int = 0) -> None:
        """Start the Squid Game (Green Light Red Light) with the given webcam index.
        Parameters:
            webcam_idx (int): The index of the webcam to use.
        """
        # Initialize screen
        screen: pygame.Surface = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Squid Games - Green Light, Red Light")

        self.loading_screen(screen, webcam_idx)

        self.game_state = SquidGame.INIT
        self.players = []  # Reset players list

        # Timing for Red/Green Light
        self.last_switch_time = time.time()

        # Compute aspect ratio and view port for webcam
        ret, frame = self.cap.read()
        if not ret:
            print("Error: Cannot read from webcam")
            return

        aspect_ratio: float = frame.shape[1] / frame.shape[0]
        x_ratio: float = frame.shape[1] / (self.WIDTH // 2)
        y_ratio: float = frame.shape[0] / ((self.WIDTH // 2) / aspect_ratio)
        view_port: tuple[int, int] = (
            int(frame.shape[1] / x_ratio),
            int(frame.shape[0] / y_ratio),
        )
        print(
            f"Ratios: {x_ratio}, {y_ratio}, Webcam: {frame.shape[1]}x{frame.shape[0]}, "
            f"Window: {self.WIDTH}x{self.HEIGHT}, View port={view_port[1]}x{view_port[0]}"
        )

        self.game_main_loop(self.cap, screen, view_port, x_ratio, y_ratio)

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
