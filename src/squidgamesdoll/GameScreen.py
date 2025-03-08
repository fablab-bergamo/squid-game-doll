import pygame
import random
import os
from PIL import Image
import cv2
from img_processing import opencv_to_pygame
from Player import Player
import constants
from LaserShooter import LaserShooter

BUTTON_COLOR: tuple[int, int, int] = (255, 0, 0)  # Red like Squid Game theme
BUTTON_HOVER_COLOR: tuple[int, int, int] = (200, 0, 0)
BUTTON_TEXT_COLOR: tuple[int, int, int] = (0, 0, 0)  # Black text
# Font Color
FONT_COLOR: tuple[int, int, int] = constants.RED


class GameScreen:
    def __init__(self):
        self._font_lcd: pygame.font.Font = pygame.font.Font(constants.ROOT + "/media/font_lcd.ttf", 48)
        self._font_small: pygame.font.Font = pygame.font.Font(constants.ROOT + "/media/SpaceGrotesk-Regular.ttf", 36)
        self._font_big: pygame.font.Font = pygame.font.Font(constants.ROOT + "/media/SpaceGrotesk-Regular.ttf", 85)
        self._button: pygame.Rect = pygame.Rect(1350, 1100, 200, 50)  # Position and size
        self._x_ratio: float = 1
        self._y_ratio: float = 1

    def set_webcam_ratios(self, ratios: tuple[float, float]) -> None:
        self._x_ratio, self._y_ratio = ratios

    def is_button_click(self, event: pygame.event):
        if self._button.collidepoint(event.pos):
            return True

    def update_screen(
        self,
        screen: pygame.Surface,
        webcam_frame: cv2.UMat,
        game_state: str,
        players: list[Player],
        shooter: LaserShooter,
    ) -> None:

        # Convert OpenCV BGR to RGB for PyGame
        video_surface: pygame.Surface = opencv_to_pygame(webcam_frame, self._view_port)

        if game_state in [constants.INIT, constants.GREEN_LIGHT, constants.RED_LIGHT]:
            self.draw_bounding_boxes(video_surface, players, game_state != constants.INIT)

        if game_state in [constants.GREEN_LIGHT, constants.RED_LIGHT]:
            self.draw_traffic_light(screen, game_state == constants.GREEN_LIGHT)

        screen.blit(video_surface, (0, 0))

        self.draw_phase_overlay(screen, game_state)

        players_surface: pygame.Surface = pygame.Surface((constants.WIDTH // 2, constants.HEIGHT))
        self.display_players(players_surface, self.convert_player_list(players), constants.SALMON)

        screen.blit(players_surface, (constants.WIDTH // 2, 0))

        if game_state not in [constants.INIT]:
            self.draw_button(screen)
            won = sum([100_000_000 for p in players if p.is_eliminated()])
            self.display_won(screen, won, self._font_big)

        if game_state == constants.GAMEOVER:
            text = self._font_big.render("GAME OVER! No vincitori...", True, constants.WHITE)
            screen.blit(text, (constants.WIDTH // 2 - 400, constants.HEIGHT - 350))

        if game_state == constants.VICTORY:
            text = self._font_big.render("VICTORY!", True, constants.DARK_GREEN)
            screen.blit(text, (constants.WIDTH // 2 - 400, constants.HEIGHT - 350))

        img: pygame.Surface = pygame.image.load(constants.ROOT + "/media/shooter_off.png")
        if shooter is not None and shooter.isOnline():
            img = pygame.image.load(constants.ROOT + "/media/shooter.png")

        # Add shooter icon depending on ESP32 status
        screen.blit(img, (constants.WIDTH - img.get_width(), 0))

    def draw_traffic_light(self, screen: pygame.Surface, green_light: bool) -> None:
        # Draw the light in the bottom part of the screen
        position: tuple[int, int] = (constants.WIDTH // 4, constants.HEIGHT // 4 * 3)
        radius: int = min(constants.WIDTH // 8, constants.HEIGHT // 8) - 4
        if green_light:
            pygame.draw.circle(screen, constants.GREEN, position, radius)
        else:
            pygame.draw.circle(screen, constants.RED, position, radius)

        pygame.draw.circle(screen, constants.BLACK, position, radius, 4)

    def draw_bounding_boxes(
        self,
        frame_surface: pygame.Surface,
        players: list[Player],
        add_previous_pos: bool = False,
    ) -> None:
        for player in players:
            color: tuple[int, int, int] = (
                constants.RED
                if player.is_eliminated()
                else (constants.GREEN if not player.has_moved() else constants.YELLOW)
            )
            x, y, w, h = player.get_rect()
            # transforms the coordinates from the webcam frame to the pygame frame using the ratios
            x, y, w, h = x / self._x_ratio, y / self._y_ratio, w / self._x_ratio, h / self._y_ratio
            pygame.draw.rect(frame_surface, color, (x, y, w, h), 3)

            # Draw the last position
            if add_previous_pos and player.get_last_position() is not None and not player.is_eliminated():
                x, y, w, h = player.get_last_rect()
                x, y, w, h = x / self._x_ratio, y / self._y_ratio, w / self._x_ratio, h / self._y_ratio
                pygame.draw.rect(frame_surface, constants.WHITE, (x, y, w, h), 1)

            if player.is_eliminated():
                pygame.draw.line(
                    frame_surface,
                    constants.RED,
                    (x, y),
                    (x + w, y + h),
                    5,
                )
                pygame.draw.line(
                    frame_surface,
                    constants.RED,
                    (x + w, y),
                    (x, y + h),
                    5,
                )

    def draw_phase_overlay(self, screen: pygame.Surface, game_state: str) -> None:
        """Display game status.

        Parameters:
            screen (pygame.Surface): The PyGame screen.
            game_state (str): Current game state.
        """
        text = self._font_small.render(f"Phase: {game_state}", True, FONT_COLOR)
        screen.blit(text, (20, screen.get_height() // 2 + 20))

    def draw_text(
        self,
        screen: pygame.Surface,
        text: str,
        location: tuple[int, int],
        color: tuple[int, int, int] = FONT_COLOR,
        size: int = 85,
    ) -> None:
        font: pygame.font.Font = pygame.font.Font(constants.ROOT + "/media/SpaceGrotesk-Regular.ttf", size)
        text_surface = font.render(text, True, color)
        screen.blit(text_surface, location)

    def draw_button(self, screen: pygame.Surface) -> None:
        mouse_pos: tuple[int, int] = pygame.mouse.get_pos()
        button_color: tuple[int, int, int] = (
            BUTTON_HOVER_COLOR if self._button.collidepoint(mouse_pos) else BUTTON_COLOR
        )
        pygame.draw.rect(screen, button_color, self._button, border_radius=10)
        text = self._font_small.render("Re-init", True, BUTTON_TEXT_COLOR)
        text_rect: pygame.Rect = text.get_rect(center=self._button.center)
        screen.blit(text, text_rect)

    # Load player images (without blur)
    def load_player_image(self, image_path: str) -> pygame.image:
        img = Image.open(image_path).convert("RGBA").resize((constants.PLAYER_SIZE, constants.PLAYER_SIZE))
        pygame_img = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
        return pygame_img

    # Arrange players in a triangle
    def get_player_positions(self, players: list, screen_width: int) -> list:
        positions = []
        start_x, start_y = screen_width // 2, -constants.PLAYER_SIZE // 2 + 100
        index = 0
        for row in range(1, 5):  # Adjust rows to fit 15 players
            x = start_x - (row * constants.PLAYER_SIZE // 2 + 20)
            y = start_y + (row * constants.PLAYER_SIZE)
            for col in range(row):
                if index < len(players):
                    positions.append((x + col * constants.PLAYER_SIZE, y))
                    index += 1
        return positions

    # Function to draw blurred diamond
    def draw_blurred_diamond(self, surface: pygame.image, x: int, y: int, size: int):
        diamond = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.polygon(
            diamond,
            (0x0F, 0x00, 0xFF, 255),
            [(size // 2, 0), (size, size // 2), (size // 2, size), (0, size // 2)],
        )
        diamond = pygame.transform.smoothscale(diamond, (size + 10, size + 10))
        diamond = pygame.transform.smoothscale(diamond, (size, size))
        surface.blit(diamond, (x, y), special_flags=pygame.BLEND_RGBA_ADD)

    def display_won(self, surface: pygame.Surface, amount: int, font: pygame.font):
        pig_img = pygame.image.load(constants.ROOT + "/media/pig.png")
        amount = f"₩ {amount:,}"
        text = font.render(amount, True, (255, 215, 0))
        pos = (0, surface.get_height() - 150)
        text_pos = (pig_img.get_width() + 50, surface.get_height() - pig_img.get_height())
        surface.blit(pig_img, pos)
        surface.blit(text, text_pos)

    # Function to mask player images into diamonds
    def mask_diamond(self, image: pygame.image) -> pygame.image:
        image = pygame.transform.scale(image, (constants.PLAYER_SIZE, constants.PLAYER_SIZE))
        mask = pygame.Surface((constants.PLAYER_SIZE, constants.PLAYER_SIZE), pygame.SRCALPHA)

        pygame.draw.polygon(
            mask,
            (255, 255, 255, 255),
            [
                (constants.PLAYER_SIZE // 2, 0),
                (constants.PLAYER_SIZE, constants.PLAYER_SIZE // 2),
                (constants.PLAYER_SIZE // 2, constants.PLAYER_SIZE),
                (0, constants.PLAYER_SIZE // 2),
            ],
        )
        masked_image = image.copy()
        masked_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        masked_image.set_colorkey((0, 0, 0))

        return masked_image

    def convert_player_list(self, players: list[Player]) -> list[dict]:
        # Creiamo un dizionario per mantenere giocatori unici con il loro stato
        risultato: list[dict] = []
        cpt: int = 1
        # Aggiungiamo i giocatori dalla lista attiva/eliminata
        for player in players:
            img = player.get_image()
            if img is None:
                img = self.load_player_image(constants.ROOT + "/media/sample_player.jpg")
            risultato.append(
                {
                    "number": cpt,
                    "active": not player.is_eliminated(),
                    "image": img,
                    "rectangle": player.get_rect(),
                    "id": player.get_id(),
                    "visible": player.is_visible(),
                }
            )
            cpt += 1
        return risultato

    def setup_ratios(self, frame: cv2.UMat):
        aspect_ratio: float = frame.shape[1] / frame.shape[0]
        self._x_ratio: float = frame.shape[1] / (constants.WIDTH // 2)
        self._y_ratio: float = frame.shape[0] / ((constants.WIDTH // 2) / aspect_ratio)
        self._view_port: tuple[int, int] = (
            int(frame.shape[1] / self._x_ratio),
            int(frame.shape[0] / self._y_ratio),
        )
        print(
            f"Ratios: {self._x_ratio}, {self._y_ratio}, Webcam: {frame.shape[1]}x{frame.shape[0]}, "
            f"Window: {constants.WIDTH}x{constants.HEIGHT}, View port={self._view_port[1]}x{self._view_port[0]}"
        )

    def display_players(
        self, screen: pygame.Surface, players: list[dict] = None, background: tuple[int, int, int] = (0, 0, 0)
    ):

        if players is None:
            players = self.fake_players()

        player_positions = self.get_player_positions(players, screen.get_width())
        screen.fill(background)

        num = sum(1 for player in players if player["active"])

        text = self._font_small.render(f"{num} Giocator{'e' if num <= 1 else 'i'}", True, constants.GREEN)
        screen.blit(text, (screen.get_width() // 2 - 100, 0))

        for i, player in enumerate(players):
            if i >= len(player_positions):
                break
            x, y = player_positions[i]

            # Draw blurred diamond
            self.draw_blurred_diamond(screen, x, y, constants.PLAYER_SIZE)

            # Draw player image
            img = player["image"].copy()
            img = self.mask_diamond(img)

            # Apply red tint
            red_overlay = pygame.Surface((constants.PLAYER_SIZE, constants.PLAYER_SIZE), pygame.SRCALPHA)
            red_overlay.fill(constants.RED)
            img.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_MULT)

            if not player["active"]:
                img.fill(constants.FADE_COLOR, special_flags=pygame.BLEND_MULT)

            # Color number according to player status
            screen.blit(img, (x, y))
            color = constants.YELLOW
            if player["visible"]:
                if player["active"]:
                    color = constants.GREEN
                else:
                    color = constants.RED

            text = self._font_small.render(str(player["number"]), True, color)
            text_rect = text.get_rect(center=(x + constants.PLAYER_SIZE // 2, y + constants.PLAYER_SIZE * 0.7))
            screen.blit(text, text_rect.topleft)
