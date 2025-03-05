import pygame
import random
import os
from PIL import Image


class GameScreen:
    ROOT = os.path.dirname(__file__)

    # Constants
    GREEN = (0, 255, 0)
    FADE_COLOR = (80, 80, 80, 80)
    RED = (180, 0, 0, 80)
    PLAYER_SIZE = 200  # Size of each player tile

    def __init__(self):
        self.FONT = pygame.font.Font(GameScreen.ROOT + "/media/font_lcd.ttf", 48)

    # Load player images (without blur)
    def load_player_image(self, image_path: str) -> pygame.image:
        img = Image.open(image_path).convert("RGBA").resize((GameScreen.PLAYER_SIZE, GameScreen.PLAYER_SIZE))
        pygame_img = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
        return pygame_img

    # Arrange players in a triangle
    def get_player_positions(self, players: list, screen_width: int) -> list:
        positions = []
        start_x, start_y = screen_width // 2, -GameScreen.PLAYER_SIZE // 2 + 100
        index = 0
        for row in range(1, 5):  # Adjust rows to fit 15 players
            x = start_x - (row * GameScreen.PLAYER_SIZE // 2 + 20)
            y = start_y + (row * GameScreen.PLAYER_SIZE)
            for col in range(row):
                if index < len(players):
                    positions.append((x + col * GameScreen.PLAYER_SIZE, y))
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
        pig_img = pygame.image.load(GameScreen.ROOT + "/media/pig.png")
        amount = f"₩ {amount:,}"
        text = font.render(amount, True, (255, 215, 0))
        pos = (0, surface.get_height() - 150)
        text_pos = (pig_img.get_width() + 50, surface.get_height() - pig_img.get_height())
        surface.blit(pig_img, pos)
        surface.blit(text, text_pos)

    # Function to mask player images into diamonds
    def mask_diamond(self, image: pygame.image) -> pygame.image:
        image = pygame.transform.scale(image, (GameScreen.PLAYER_SIZE, GameScreen.PLAYER_SIZE))
        mask = pygame.Surface((GameScreen.PLAYER_SIZE, GameScreen.PLAYER_SIZE), pygame.SRCALPHA)

        pygame.draw.polygon(
            mask,
            (255, 255, 255, 255),
            [
                (GameScreen.PLAYER_SIZE // 2, 0),
                (GameScreen.PLAYER_SIZE, GameScreen.PLAYER_SIZE // 2),
                (GameScreen.PLAYER_SIZE // 2, GameScreen.PLAYER_SIZE),
                (0, GameScreen.PLAYER_SIZE // 2),
            ],
        )
        masked_image = image.copy()
        masked_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        masked_image.set_colorkey((0, 0, 0))

        return masked_image

    def fake_players(self) -> list:
        # Generate players list (maximum 10 players)
        players = []
        for num in range(1, 16):
            players.append(
                {
                    "number": num,
                    "active": random.choice([True, False]),
                    "image": self.load_player_image(GameScreen.ROOT + "/media/sample_player.jpg"),
                    "rectangle": (0, 0, 0, 0),
                }
            )
        return players

    # Game loop
    def display_players(
        self, screen: pygame.Surface, players: list = None, background: tuple[int, int, int] = (0, 0, 0)
    ):

        if players is None:
            players = self.fake_players()

        player_positions = self.get_player_positions(players, screen.get_width())
        screen.fill(background)

        num = sum(1 for player in players if player["active"])

        text = self.FONT.render(f"{num} Giocatori", True, GameScreen.GREEN)
        screen.blit(text, (screen.get_width() // 2 - 100, 0))

        for i, player in enumerate(players):
            if i >= len(player_positions):
                break
            x, y = player_positions[i]

            # Draw blurred diamond
            self.draw_blurred_diamond(screen, x, y, GameScreen.PLAYER_SIZE)

            # Draw player image
            img = player["image"].copy()
            img = self.mask_diamond(img)

            # Apply red tint
            red_overlay = pygame.Surface((GameScreen.PLAYER_SIZE, GameScreen.PLAYER_SIZE), pygame.SRCALPHA)
            red_overlay.fill(GameScreen.RED)
            img.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_MULT)

            if not player["active"]:
                img.fill(GameScreen.FADE_COLOR, special_flags=pygame.BLEND_MULT)

            screen.blit(img, (x, y))

            text = self.FONT.render(
                str(player["number"]), True, GameScreen.GREEN if player["active"] else GameScreen.RED
            )
            text_rect = text.get_rect(center=(x + GameScreen.PLAYER_SIZE // 2, y + GameScreen.PLAYER_SIZE * 0.7))
            screen.blit(text, text_rect.topleft)
