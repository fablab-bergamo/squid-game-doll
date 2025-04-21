import pygame
import cv2
from collections.abc import Callable
from PIL import Image

from .img_processing import opencv_to_pygame
from .Player import Player
from .LaserShooter import LaserShooter
from .GameSettings import GameSettings
from .constants import (
    RED,
    ROOT,
    DARK_GREEN,
    SALMON,
    BLACK,
    WHITE,
    GREEN,
    YELLOW,
    PLAYER_SIZE,
    FADE_COLOR,
    VICTORY,
    GAMEOVER,
    INIT,
    GREEN_LIGHT,
    RED_LIGHT,
)
from loguru import logger

BUTTON_COLOR: tuple[int, int, int] = (255, 0, 0)  # Red like Squid Game theme
BUTTON_HOVER_COLOR: tuple[int, int, int] = (200, 0, 0)
BUTTON_TEXT_COLOR: tuple[int, int, int] = (0, 0, 0)  # Black text
# Font Color
FONT_COLOR: tuple[int, int, int] = RED


class GameScreen:
    def __init__(self, desktop_size: tuple[int, int], display_idx: int):
        self._font_lcd: pygame.font.FontType = pygame.font.Font(ROOT + "/media/font_lcd.ttf", 48)
        self._font_small: pygame.font.FontType = pygame.font.Font(ROOT + "/media/SpaceGrotesk-Regular.ttf", 36)
        self._font_button: pygame.font.FontType = pygame.font.Font(ROOT + "/media/SpaceGrotesk-Bold.ttf", 42)
        self._font_smaller: pygame.font.FontType = pygame.font.Font(ROOT + "/media/SpaceGrotesk-Regular.ttf", 24)
        self._font_big: pygame.font.FontType = pygame.font.Font(ROOT + "/media/SpaceGrotesk-Regular.ttf", 90)
        self._font_bigger: pygame.font.FontType = pygame.font.Font(ROOT + "/media/SpaceGrotesk-Bold.ttf", 128)

        # Position and size of reinit button
        self._reset_button: pygame.Rect = pygame.Rect(desktop_size[0] - 210, desktop_size[1] - 60, 200, 50)
        self._config_button: pygame.Rect = pygame.Rect(desktop_size[0] - 210, desktop_size[1] - 60 - 50 - 10, 200, 50)

        self._ratio: float = 1
        self._desktop_size: tuple[int, int] = desktop_size
        self._display_idx = display_idx

        self._first_run = True
        self._active_buttons = {}
        self._click_callback = None

    def reset_active_buttons(self):
        self._active_buttons = {}
        self._click_callback = None

    def set_active_button(self, idx: int, callback: Callable) -> None:
        if callback == None:
            del self._active_buttons[idx]

        self._active_buttons[idx] = callback

    def set_click_callback(self, callback: Callable) -> None:
        self._click_callback = callback

    def get_button_color(self, idx: int) -> pygame.Color:
        if idx == 1:
            return (255, 0, 0)
        elif idx == 2:
            return (255, 255, 0)
        elif idx == 3:
            return (0, 255, 0)
        elif idx == 0:
            return (0, 0, 255)

        return (255, 0, 0)

    def get_button_text(self, idx: int) -> str:
        if idx == 1:
            return "A"
        elif idx == 2:
            return "B"
        elif idx == 3:
            return "Y"
        elif idx == 0:
            return "X"
        return "?"

    def draw_active_buttons(self, surface: pygame.Surface) -> None:
        for idx, _ in self._active_buttons.items():
            y_pos = surface.get_height() - (len(self._active_buttons) - idx) * 90
            center = (surface.get_width() - 45, y_pos)
            pygame.draw.circle(surface, self.get_button_color(idx), center, 40)
            text = self._font_button.render(self.get_button_text(idx), True, BLACK, self.get_button_color(idx))
            surface.blit(text, (center[0] - text.get_width() // 2, center[1] - text.get_height() // 2))

    def handle_buttons(self, joystick: pygame.joystick.JoystickType) -> bool:
        if joystick == None:
            return True
        for idx, fun in self._active_buttons.items():
            if joystick.get_button(idx):
                logger.debug(f"Joystick button {idx}: calling {fun.__name__}")
                return fun()
        return True

    def handle_buttons_click(self, surface: pygame.Surface, event: pygame.event) -> bool:
        for idx, fun in self._active_buttons.items():
            y_pos = surface.get_height() - (len(self._active_buttons) - idx) * 90
            v1 = pygame.math.Vector2(surface.get_width() - 45, y_pos)
            v2 = pygame.math.Vector2(pygame.mouse.get_pos())
            if v1.distance_to(v2) < 40:
                logger.debug(f"Click on button {idx}: calling {fun.__name__}")
                return fun()
        if self._click_callback is not None:
            return self._click_callback(event)
        return True

    def get_desktop_width(self) -> int:
        return self._desktop_size[0]

    def get_desktop_height(self) -> int:
        return self._desktop_size[1]

    def get_display_idx(self) -> int:
        return self._display_idx

    def is_reset_button_click(self, event: pygame.event) -> bool:
        if self._reset_button.collidepoint(event.pos):
            return True
        return False

    def is_config_button_click(self, event: pygame.event) -> bool:
        if self._config_button.collidepoint(event.pos):
            return True
        return False

    def update_config(self, fullscreen: pygame.Surface, webcam_frame: cv2.UMat, shooter: LaserShooter) -> None:

        fullscreen.fill(DARK_GREEN)

        (w, h), (x_web, y_web) = self.compute_webcam_feed(webcam_frame)

        # Convert OpenCV BGR to RGB for PyGame
        video_surface: pygame.Surface = opencv_to_pygame(webcam_frame, (w, h))

        fullscreen.blit(video_surface, (x_web, y_web))

        self.draw_reset_button(fullscreen)

        img: pygame.Surface = pygame.image.load(ROOT + "/media/shooter_off.png")
        if shooter is not None and shooter.isOnline():
            img = pygame.image.load(ROOT + "/media/shooter.png")

        # Add shooter icon depending on ESP32 status
        fullscreen.blit(img, (self.get_desktop_width() - img.get_width(), 0))

        self.draw_active_buttons(fullscreen)

    def update(
        self,
        fullscreen: pygame.Surface,
        nn_frame: cv2.UMat,
        game_state: str,
        players: list[Player],
        shooter: LaserShooter,
        settings: GameSettings,
    ) -> None:

        fullscreen.fill(SALMON)

        (w, h), (x_web, y_web) = self.compute_webcam_feed(nn_frame)

        # Convert OpenCV BGR to RGB for PyGame
        video_surface: pygame.Surface = opencv_to_pygame(nn_frame, (w, h))

        if game_state in [INIT, GREEN_LIGHT, RED_LIGHT]:
            self.draw_finish_area(video_surface, settings)

        self.draw_bounding_boxes(video_surface, players, game_state != INIT)

        video_surface = pygame.transform.flip(video_surface, True, False)
        fullscreen.blit(video_surface, (x_web, y_web))

        if game_state in [GREEN_LIGHT, RED_LIGHT]:
            self.draw_traffic_light(fullscreen, game_state == GREEN_LIGHT)

        players_surface: pygame.Surface = pygame.Surface((self.get_desktop_width(), PLAYER_SIZE))

        self.display_players(players_surface, self._convert_player_list(players), SALMON, game_state == VICTORY)

        fullscreen.blit(players_surface, (0, self.get_desktop_height() - PLAYER_SIZE))

        if game_state not in [INIT]:
            won = sum([100_000_000 for p in players if p.is_eliminated()])
            self.display_won(fullscreen, won, self._font_big)

        if game_state == GAMEOVER:
            text = self._font_bigger.render("GAME OVER!", True, RED)
            fullscreen.blit(
                text,
                (
                    (self.get_desktop_width() - text.get_width()) // 2,
                    (self.get_desktop_height() - text.get_height()) // 2,
                ),
            )

        if game_state == VICTORY:
            text = self._font_bigger.render("VICTORY!", True, GREEN)
            fullscreen.blit(
                text,
                (
                    (self.get_desktop_width() - text.get_width()) // 2,
                    (self.get_desktop_height() - text.get_height()) // 2,
                ),
            )

        img: pygame.Surface = pygame.image.load(ROOT + "/media/shooter_off.png")
        if shooter is not None and shooter.isOnline():
            img = pygame.image.load(ROOT + "/media/shooter.png")

        # Add shooter icon depending on ESP32 status
        fullscreen.blit(img, (self.get_desktop_width() - img.get_width(), 0))

        self.draw_active_buttons(fullscreen)

    def draw_traffic_light(self, screen: pygame.Surface, green_light: bool) -> None:
        # Draw the light in the bottom part of the screen
        radius: int = min(self.get_desktop_width() // 20, self.get_desktop_height() // 20) - 4
        position: tuple[int, int] = (
            self.get_desktop_width() - radius,
            min(radius * 5, self.get_desktop_height() - radius - 4),
        )
        if green_light:
            pygame.draw.circle(screen, GREEN, position, radius)
        else:
            pygame.draw.circle(screen, RED, position, radius)

        pygame.draw.circle(screen, BLACK, position, radius, 4)

    def draw_bounding_boxes(
        self,
        frame_surface: pygame.Surface,
        players: list[Player],
        add_previous_pos: bool = False,
    ) -> None:
        for player in players:
            color: tuple[int, int, int] = (
                RED if player.is_eliminated() else (GREEN if not player.has_moved() else YELLOW)
            )
            x, y, w, h = player.get_rect()
            # transforms the coordinates from the webcam frame to the pygame frame using the ratios
            x, y, w, h = x / self._ratio, y / self._ratio, w / self._ratio, h / self._ratio
            # Flip along central vertical
            pygame.draw.rect(frame_surface, color, (x, y, w, h), 3, border_radius=10)

            render = self._font_smaller.render(str(player.get_id()), True, color)
            render = pygame.transform.flip(render, True, False)
            text_rect: pygame.Rect = render.get_rect(
                center=(x + w // 2, max(render.get_height() // 2, y - render.get_height() // 2))
            )
            # frame_surface.blit(render, text_rect)

            # Draw the last position
            if add_previous_pos and player.get_last_position() is not None and not player.is_eliminated():
                x, y, w, h = player.get_last_rect()
                x, y, w, h = x / self._ratio, y / self._ratio, w / self._ratio, h / self._ratio
                pygame.draw.rect(frame_surface, WHITE, (x, y, w, h), 1, border_radius=10)

            if player.is_eliminated():
                pygame.draw.line(
                    frame_surface,
                    RED,
                    (x, y),
                    (x + w, y + h),
                    10,
                )
                pygame.draw.line(
                    frame_surface,
                    RED,
                    (x + w, y),
                    (x, y + h),
                    10,
                )

    def draw_phase_overlay(self, surface: pygame.Surface, game_state: str) -> None:
        """Display game status.

        Parameters:
            surface (pygame.Surface): The PyGame screen.
            game_state (str): Current game state.
        """
        text = self._font_small.render(f"Fase: {game_state}", True, FONT_COLOR)
        surface.blit(text, (surface.get_width() // 2 + 20, 20))

    def draw_finish_area(self, webcam_surface: pygame.Surface, settings: GameSettings):
        # Draw the rectangles of finish area
        for rect in settings.areas["finish"]:
            # Scale the rectangle to the webcam surface size
            scaled_rect = pygame.Rect(
                rect.x * webcam_surface.get_width() / settings.get_reference_frame().width,
                rect.y * webcam_surface.get_height() / settings.get_reference_frame().height,
                rect.width * webcam_surface.get_width() / settings.get_reference_frame().width,
                rect.height * webcam_surface.get_height() / settings.get_reference_frame().height,
            )
            # Draw the rectangles
            pygame.draw.rect(webcam_surface, YELLOW, scaled_rect, 2, border_radius=10)

    def draw_text(
        self,
        screen: pygame.Surface,
        text: str,
        location: tuple[int, int],
        color: tuple[int, int, int] = FONT_COLOR,
        size: int = 85,
    ) -> None:
        font: pygame.font.FontType = pygame.font.Font(ROOT + "/media/SpaceGrotesk-Regular.ttf", size)
        text_surface = font.render(text, True, color)
        screen.blit(text_surface, location)

    def draw_reset_button(self, screen: pygame.Surface) -> None:
        mouse_pos: tuple[int, int] = pygame.mouse.get_pos()
        button_color: tuple[int, int, int] = (
            BUTTON_HOVER_COLOR if self._reset_button.collidepoint(mouse_pos) else BUTTON_COLOR
        )
        pygame.draw.rect(screen, button_color, self._reset_button, border_radius=10)
        text = self._font_small.render("Re-init", True, BUTTON_TEXT_COLOR)
        text_rect: pygame.Rect = text.get_rect(center=self._reset_button.center)
        screen.blit(text, text_rect)

    def draw_config_button(self, screen: pygame.Surface) -> None:
        mouse_pos: tuple[int, int] = pygame.mouse.get_pos()
        button_color: tuple[int, int, int] = (
            BUTTON_HOVER_COLOR if self._config_button.collidepoint(mouse_pos) else BUTTON_COLOR
        )
        pygame.draw.rect(screen, button_color, self._config_button, border_radius=10)
        text = self._font_small.render("Config", True, BUTTON_TEXT_COLOR)
        text_rect: pygame.Rect = text.get_rect(center=self._config_button.center)
        screen.blit(text, text_rect)

    # Load player images (without blur)
    def load_player_image(self, image_path: str) -> pygame.image:
        img = Image.open(image_path).convert("RGBA").resize((PLAYER_SIZE, PLAYER_SIZE))
        pygame_img = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
        return pygame_img

    # Arrange players in a triangle
    def get_player_positions(self, players: list, screen_width: int) -> list:
        positions = []
        start_x, start_y = 0, 0
        for cpt, _ in enumerate(players):
            x = start_x + (cpt * PLAYER_SIZE + 20)
            y = start_y
            if x > self._desktop_size[0]:
                logger.warning("Too many players")
                break
            positions.append((x, y))
        return positions

    # Function to draw blurred diamond
    def draw_blurred_diamond(self, surface: pygame.image, x: int, y: int, size: int) -> None:
        diamond = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.polygon(
            diamond,
            (0x0F, 0x00, 0xFF, 255),
            [(size // 2, 0), (size, size // 2), (size // 2, size), (0, size // 2)],
        )
        diamond = pygame.transform.smoothscale(diamond, (size + 10, size + 10))
        diamond = pygame.transform.smoothscale(diamond, (size, size))
        surface.blit(diamond, (x, y), special_flags=pygame.BLEND_RGBA_ADD)

    def display_won(self, surface: pygame.Surface, amount: int, font: pygame.font.FontType) -> None:
        pig_img = pygame.image.load(ROOT + "/media/pig.png")
        amount = f"₩ {amount:,}"
        text = font.render(amount, True, (255, 215, 0))
        pos = (surface.get_width() // 3, 0)
        text_pos = (pos[0] + pig_img.get_width() + 50, (pig_img.get_height() - text.get_height()) // 2)
        surface.blit(pig_img, pos)
        surface.blit(text, text_pos)

    # Function to mask player images into diamonds
    def mask_diamond(self, image: pygame.image) -> pygame.image:
        image = pygame.transform.scale(image, (PLAYER_SIZE, PLAYER_SIZE))
        mask = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)

        pygame.draw.polygon(
            mask,
            (255, 255, 255, 255),
            [
                (PLAYER_SIZE // 2, 0),
                (PLAYER_SIZE, PLAYER_SIZE // 2),
                (PLAYER_SIZE // 2, PLAYER_SIZE),
                (0, PLAYER_SIZE // 2),
            ],
        )
        masked_image = image.copy()
        masked_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        masked_image.set_colorkey((0, 0, 0))

        return masked_image

    def _convert_player_list(self, players: list[Player]) -> list[dict]:
        # Creiamo un dizionario per mantenere giocatori unici con il loro stato
        risultato: list[dict] = []
        cpt: int = 1
        # Aggiungiamo i giocatori dalla lista attiva/eliminata
        for player in players:
            img = player.get_image()
            if img is None:
                img = self.load_player_image(ROOT + "/media/sample_player.jpg")
            risultato.append(
                {
                    "number": cpt,
                    "active": not player.is_eliminated() and not player.is_winner(),
                    "image": img,
                    "rectangle": player.get_rect(),
                    "id": player.get_id(),
                    "visible": player.is_visible(),
                    "winner": player.is_winner(),
                    "eliminated": player.is_eliminated(),
                }
            )
            cpt += 1
        return risultato

    def compute_webcam_feed(self, frame: cv2.UMat) -> tuple[tuple[int, int], tuple[int, int]]:

        w1, h1 = self.get_desktop_width(), self.get_desktop_height()
        h2, w2, _ = frame.shape

        # Available height after reserving the PLAYER_SIZE band
        available_height = h1 - PLAYER_SIZE

        # Compute the scaling factor to fit within the screen while maintaining aspect ratio
        scale_x = w1 / w2
        scale_y = available_height / h2
        scale = min(scale_x, scale_y)  # Choose the smaller scaling factor to fit fully

        # Compute the new dimensions of the webcam feed
        w3 = int(w2 * scale)
        h3 = int(h2 * scale)

        # Center the webcam feed on the screen
        x = (w1 - w3) // 2
        y = (available_height - h3) // 2

        self._ratio = w2 / w3
        if self._first_run:
            logger.debug(
                f"Webcam {w2, h2} -> on screen {w1, h1} : {w3, h3} in position {x, y} (webcam-to-screen ratio {self._ratio})"
            )
            self._first_run = False

        return (w3, h3), (x, y)

    def display_players(
        self,
        screen: pygame.Surface,
        players: list[dict] = None,
        background: tuple[int, int, int] = (0, 0, 0),
        game_ended: bool = False,
    ) -> None:

        player_positions = self.get_player_positions(players, screen.get_width())
        screen.fill(background)

        num = sum(1 for player in players if player["active"])

        text = self._font_small.render(f"{num} giocator{'e' if num <= 1 else 'i'}", True, GREEN)
        screen.blit(text, ((screen.get_width() - text.get_width()) // 2, screen.get_height() - text.get_height()))

        for i, player in enumerate(players):
            if i >= len(player_positions):
                break
            x, y = player_positions[i]

            # Draw blurred diamond
            self.draw_blurred_diamond(screen, x, y, PLAYER_SIZE)

            # Draw player image
            img = player["image"]
            img = self.mask_diamond(img)

            # Apply red tint
            red_overlay = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
            red_overlay.fill(GREEN if player["winner"] else RED)
            img.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_MULT)

            if not player["active"]:
                img.fill(FADE_COLOR, special_flags=pygame.BLEND_MULT)

            # Color number according to player status
            screen.blit(img, (x, y))
            color = YELLOW
            if player["visible"]:
                if player["active"]:
                    color = GREEN
                else:
                    color = RED

            if game_ended and player["winner"]:
                total_prize = 100_000_000 * len([p for p in players if p["eliminated"]])
                per_person = total_prize // len([p for p in players if p["winner"]])
                text = self._font_smaller.render(f"₩ {per_person:,}", True, YELLOW)
                text_rect = text.get_rect(center=(x + PLAYER_SIZE // 2, y + PLAYER_SIZE * 0.8))
            else:
                text = self._font_lcd.render(str(player["id"]), True, color)
                text_rect = text.get_rect(center=(x + PLAYER_SIZE // 2, y + PLAYER_SIZE * 0.7))
            screen.blit(text, text_rect.topleft)

    @staticmethod
    def get_desktop(preferred_monitor=0) -> tuple[tuple[int, int], int]:
        num = 0
        for size in pygame.display.get_desktop_sizes():
            if num == preferred_monitor:
                return (size, preferred_monitor)
            num += 1
        return (pygame.display.get_desktop_sizes()[0], 0)
