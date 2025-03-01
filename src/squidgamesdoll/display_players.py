import pygame
import random
import os
from pygame import gfxdraw
from PIL import Image, ImageFilter


# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 800
BG_COLOR = (0, 0, 0)
GREEN = (0, 255, 0)
FADE_COLOR = (80, 80, 80)
RED_TINT = (180, 0, 0)
PLAYER_SIZE = 200  # Size of each player tile

# Load player images (without blur)
def load_player_image(image_path):
    img = Image.open(image_path).convert("RGBA").resize((PLAYER_SIZE, PLAYER_SIZE))
    pygame_img = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
    return pygame_img


# Arrange players in a triangle
def get_player_positions(players):
    positions = []
    start_x, start_y = SCREEN_WIDTH // 2, -PLAYER_SIZE // 2 + 100
    index = 0
    for row in range(1, 5):  # Adjust rows to fit 15 players
        x = start_x - (row * PLAYER_SIZE // 2)
        y = start_y + (row * (PLAYER_SIZE // 2 + 10))
        for col in range(row):
            if index < len(players):
                positions.append((x + col * PLAYER_SIZE, y))
                index += 1
    return positions

# Function to draw blurred diamond
def draw_blurred_diamond(surface, x, y, size):
    diamond = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.polygon(diamond, (0x0F, 0x00, 0xFF, 255), [(size//2, 0), (size, size//2), (size//2, size), (0, size//2)])
    diamond = pygame.transform.smoothscale(diamond, (size+10, size+10))
    diamond = pygame.transform.smoothscale(diamond, (size, size))
    surface.blit(diamond, (x, y), special_flags=pygame.BLEND_RGBA_ADD)

# Function to mask player images into diamonds
def mask_diamond(image):
    mask = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), [(PLAYER_SIZE//2, 0), (PLAYER_SIZE, PLAYER_SIZE//2), (PLAYER_SIZE//2, PLAYER_SIZE), (0, PLAYER_SIZE//2)])
    masked_image = image.copy()
    masked_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return masked_image

def fake_players():
    # Generate players list (maximum 10 players)
    players = []
    for num in range(1, 16):
        players.append({
            "number": num,
            "active": random.choice([True, False]),
            "image": load_player_image(os.path.dirname(__file__) + "/media/sample_player.jpg")  # Replace with actual image paths
        })
    return players

# Game loop
def display_players(screen: pygame.Surface, players: list = None):
    ROOT = os.path.dirname(__file__)
    FONT = pygame.font.Font(ROOT + "/media/font_lcd.ttf", 48)
    if players is None:
        players = fake_players()
    player_positions = get_player_positions(players)
    screen.fill(BG_COLOR)
    num = sum(1 for player in players if player["active"])
    text = FONT.render(f"{num} Giocatori", True, GREEN)
    screen.blit(text, (SCREEN_WIDTH // 2 - 100, 0))
    
    for i, player in enumerate(players):
        if i >= len(player_positions):
            break
        x, y = player_positions[i]
        
        # Draw blurred diamond
        draw_blurred_diamond(screen, x, y, PLAYER_SIZE)
        
        # Draw player image
        img = player["image"].copy()
        img = mask_diamond(img)
        
        # Apply red tint
        red_overlay = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE), pygame.SRCALPHA)
        red_overlay.fill(RED_TINT)
        img.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_MULT)
        
        if not player["active"]:
            img.fill(FADE_COLOR, special_flags=pygame.BLEND_MULT)
        
        screen.blit(img, (x, y))
        
        text = FONT.render(str(player["number"]), True, GREEN if player["active"] else RED_TINT)
        text_rect = text.get_rect(center=(x + PLAYER_SIZE // 2, y + PLAYER_SIZE * 0.7))
        screen.blit(text, text_rect.topleft)
       
