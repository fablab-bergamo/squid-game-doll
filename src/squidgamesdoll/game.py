import pygame
import cv2
import numpy as np
import random
import time
import os
from display_players import display_players, load_player_image
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
        # Constants
        self.FONT: pygame.font.Font = pygame.font.Font(None, 36)
        self.FONT_FINE: pygame.font.Font = pygame.font.Font(None, 85)

        # Colors and File Paths
        self.ROOT: str = os.path.dirname(__file__)
        self.previous_time: float = time.time()
        self.previous_positions: list = []  # List of bounding boxes (tuples)
        self.tracker: PlayerTracker = PlayerTracker()
        self.FAKE: bool = False
        self.face_extractor: FaceExtractor = FaceExtractor()
        self.players: list[Player] = []
        self.green_sound: pygame.mixer.Sound = pygame.mixer.Sound(self.ROOT + "/media/green_light.mp3")
        self.red_sound: pygame.mixer.Sound = pygame.mixer.Sound(
            self.ROOT + "/media/red_light.mp3"
        )  # 무궁화 꽃이 피었습니다
        self.eliminate_sound: pygame.mixer.Sound = pygame.mixer.Sound(self.ROOT + "/media/eliminated.mp3")
        self.game_state: str = self.INIT
        self.last_switch_time: float = time.time()
        self.delay_s: int = random.randint(2, 5)

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
                img = load_player_image(os.path.join(os.path.dirname(__file__), "media/sample_player.jpg"))
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
        position: tuple[int, int] = (self.WIDTH // 2, self.HEIGHT - 100)
        if green_light:
            pygame.draw.circle(screen, self.GREEN, position, 50)
        else:
            pygame.draw.circle(screen, self.RED, position, 50)

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
            # Update player position, or create a new player
            if p is not None:
                p.set_coords(new_p.get_coords())
            else:
                players.append(new_p)
        return players

    def loading_screen(self, screen: pygame.Surface) -> None:
        # Load sounds
        intro_sound: pygame.mixer.Sound = pygame.mixer.Sound(self.ROOT + "/media/intro.mp3")
        # add loading screen picture during intro sound
        loading_screen_img = pygame.image.load(self.ROOT + "/media/loading_screen.webp")
        loading_screen_img = pygame.transform.scale(loading_screen_img, (self.WIDTH, self.HEIGHT))
        screen.blit(loading_screen_img, (0, 0))
        pygame.display.flip()
        intro_sound.play()

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
            ret, frame = cap.read()
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
                        screen.fill((80, 80, 80))

            # Game Logic
            if self.game_state == SquidGame.INIT:
                self.players = self.tracker.process_frame(frame)
                self.draw_overlay(screen, self.game_state)
                text = self.FONT.render("Waiting for players...", True, self.FONT_COLOR)
                screen.blit(text, (self.WIDTH // 2 - 100, self.HEIGHT // 2))
                while len(self.players) < 1:
                    pygame.display.flip()
                    ret, frame = cap.read()
                    if not ret:
                        break
                    self.players = self.tracker.process_frame(frame)
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                            continue
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
            elif self.game_state in [SquidGame.GAMEOVER, SquidGame.VICTORY]:
                # Restart after 10 seconds
                if time.time() - self.last_switch_time > 20:
                    self.game_state = SquidGame.INIT
                    self.players.clear()
                    self.last_switch_time = time.time()
                    screen.fill((0, 0, 0))
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
            display_players(
                players_surface,
                self.convert_player_list(self.players),
            )

            # Show webcam feed
            screen.blit(frame_surface, (0, 0))
            # Show players screen
            screen.blit(players_surface, (self.WIDTH // 2, 0))
            self.draw_button(screen)
            # Add game status
            self.draw_light(screen, green_light)

            if self.game_state == SquidGame.GAMEOVER:
                text = self.FONT_FINE.render("GAME OVER! No vincitori...", True, (255, 0, 0))
                screen.blit(text, (self.WIDTH // 2 - 300, self.HEIGHT - 250))

            if self.game_state == SquidGame.VICTORY:
                text = self.FONT_FINE.render("VICTORY!", True, (0, 255, 0))
                screen.blit(text, (self.WIDTH // 2 - 200, self.HEIGHT - 250))

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
        pygame.display.set_caption("Squid Game - Green Light Red Light")

        self.loading_screen(screen)

        # Disable hardware acceleration for webcam on Windows
        os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
        # Use DSHOW on Windows to avoid slow startup
        cap: cv2.VideoCapture = cv2.VideoCapture(webcam_idx, cv2.CAP_DSHOW)

        # Configure webcam stream settings
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
        cap.set(cv2.CAP_PROP_FPS, 15.0)

        # Wait for intro sound to finish
        while pygame.mixer.get_busy():
            pygame.event.get()

        screen.fill((0, 0, 0))

        self.game_state = SquidGame.INIT
        self.players = []  # Reset players list

        # Timing for Red/Green Light
        self.last_switch_time = time.time()

        # Compute aspect ratio and view port for webcam
        ret, frame = cap.read()
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

        self.game_main_loop(cap, screen, view_port, x_ratio, y_ratio)

        # Cleanup
        cap.release()


if __name__ == "__main__":
    game = SquidGame()
    index: int = Camera.getCameraIndex()
    if index == -1:
        print("No compatible webcam found")
        exit(1)
    game.start_game(index)
