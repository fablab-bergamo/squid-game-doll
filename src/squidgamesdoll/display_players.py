import pygame
import random
import os
from pygame import gfxdraw
from PIL import Image, ImageFilter

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 800
BG_COLOR = (0, 0, 0)
GREEN = (0, 255, 0)
FADE_COLOR = (100, 100, 100)
RED_TINT = (150, 0, 0)
PLAYER_SIZE = 150  # Size of each player tile
FONT = pygame.font.Font(None, 48)

# Load player images (without blur)
def load_player_image(image_path):
    img = Image.open(image_path).convert("RGBA").resize((PLAYER_SIZE, PLAYER_SIZE))
    pygame_img = pygame.image.fromstring(img.tobytes(), img.size, "RGBA")
    return pygame_img

# Generate players list (maximum 15 players)
players = []
for num in range(1, 16):
    players.append({
        "number": num,
        "active": random.choice([True, False]),
        "image": load_player_image(os.path.dirname(__file__) + "/media/sample_player.jpg")  # Replace with actual image paths
    })

# Arrange players in a triangle
def get_player_positions():
    positions = []
    start_x, start_y = SCREEN_WIDTH // 2, 50
    index = 0
    for row in range(1, 6):  # Adjust rows to fit 15 players
        x = start_x - (row * PLAYER_SIZE // 2)
        y = start_y + (row * PLAYER_SIZE)
        for col in range(row):
            if index < len(players):
                positions.append((x + col * PLAYER_SIZE, y))
                index += 1
    return positions

player_positions = get_player_positions()

# Create display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Squid Game Player Grid")

# Function to draw blurred diamond
def draw_blurred_diamond(surface, x, y, size):
    diamond = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.polygon(diamond, (64, 64, 64, 255), [(size//2, 0), (size, size//2), (size//2, size), (0, size//2)])
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

# Game loop
running = True
while running:
    screen.fill(BG_COLOR)
    
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
        
        if player["active"]:
            text = FONT.render(str(player["number"]), True, GREEN)
            text_rect = text.get_rect(center=(x + PLAYER_SIZE // 2, y + PLAYER_SIZE * 0.7))
            screen.blit(text, text_rect.topleft)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    pygame.display.flip()

pygame.quit()
