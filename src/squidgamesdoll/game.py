import pygame
import cv2
import numpy as np
import random
import time
import os
from display_players import display_players, load_player_image

# Initialize PyGame
pygame.init()

# Constants
WIDTH, HEIGHT = 1600, 1200
FONT = pygame.font.Font(None, 36)

# Colors
GREEN = (0, 255, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

FONT_COLOR = BLACK

# Initialize screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
#pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("Squid Game - Green Light Red Light")

# Load sounds
ROOT = os.path.dirname(__file__)
intro_sound = pygame.mixer.Sound(ROOT + "/media/intro.mp3")
green_sound = pygame.mixer.Sound(ROOT + "/media/green_light.mp3")
# 무궁화 꽃이 피었습니다
red_sound = pygame.mixer.Sound(ROOT + "/media/red_light.mp3")
eliminate_sound = pygame.mixer.Sound(ROOT + "/media/eliminated.mp3")

# add loading screen picture during intro sound
loading_screen = pygame.image.load(ROOT + "/media/loading_screen.webp")
screen.blit(loading_screen, (0, 0))
pygame.display.flip()
intro_sound.play()

os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

# OpenCV webcam setup
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

while pygame.mixer.get_busy():
    pygame.event.get()

# Game States
INIT, GREEN_LIGHT, RED_LIGHT, VICTORY = "INIT", "GREEN_LIGHT", "RED_LIGHT", "VICTORY"
game_state = INIT

# Simulated external player detection (bounding boxes format: [x, y, w, h])
players = []
eliminated_players = set()
num_players = 5  # Simulating external detection

# Fake player detection (simulated bounding boxes)
previous_time = time.time()
previous_positions = [(0, 0, 0, 0)] * num_players


def detect_players(num_players: int):
    """Simulate an external detection system returning bounding boxes."""
    global previous_time, previous_positions
    if time.time() - previous_time > 1:
        previous_time = time.time()
        previous_positions = [
            (random.randint(100, 700), random.randint(100, 500), 80, 120)
            for _ in range(num_players)
            ]
    return previous_positions

# Timing for Red/Green Light
last_switch_time = time.time()
green_light = True

def draw_overlay():
    """Display game status."""
    text = FONT.render(f"Phase: {game_state}", True, FONT_COLOR)
    screen.blit(text, (20, 20))

def process_red_light(new_positions):
    """Eliminate players who moved during Red Light."""
    global eliminated_players
    for i, (x, y, w, h) in enumerate(new_positions):
        if i not in eliminated_players and players[i] != (x, y, w, h) and random.randint(0, 100) == 0:
            eliminated_players.add(i)
            eliminate_sound.play()


def merge_players(players, eliminated) -> list:
    # Creiamo un dizionario per mantenere giocatori unici con il loro stato
    risultato = []
    cpt = 1
    # Aggiungiamo i giocatori dalla lista attiva/eliminata
    for player in players:
        risultato.append({
            "number": cpt,
            "active": True,
            "image": load_player_image(os.path.dirname(__file__) + "/media/sample_player.jpg")
            })
        cpt += 1
    
    # Aggiungiamo i giocatori dalla lista eliminata, forzando lo stato a False
    for player in eliminated:
        risultato[player]["active"] = False
    
    return risultato


screen.fill((0,0,0))

delay = random.randint(1, 5)

# Game Loop
running = True
while running:
    ret, frame = cap.read()
    if not ret:
        break

    # Convert OpenCV BGR to RGB for PyGame
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.rot90(frame)  # Rotate to match PyGame coordinates
    frame = cv2.resize(frame, (WIDTH // 2, HEIGHT))
    frame_surface = pygame.surfarray.make_surface(frame)
    screen.blit(frame_surface, (0, 0))  # Show webcam feed

    # Handle Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Game Logic
    if game_state == INIT:
        players = detect_players(5)
        draw_overlay()
        text = FONT.render("Waiting for players...", True, FONT_COLOR)
        screen.blit(text, (WIDTH // 2 - 100, HEIGHT // 2))
        pygame.display.flip()
        time.sleep(2)
        game_state = GREEN_LIGHT
        green_sound.play()

    elif game_state in [GREEN_LIGHT, RED_LIGHT]:
        # Switch phase randomly (1-5 seconds)
        if time.time() - last_switch_time > delay:
            green_light = not green_light
            last_switch_time = time.time()
            game_state = GREEN_LIGHT if green_light else RED_LIGHT
            (red_sound if green_light else green_sound).stop()
            (green_sound if green_light else red_sound).play()
            delay = random.randint(1, 5)

        # New player positions (simulating new detections)
        new_positions = detect_players(len(players))

        if not green_light:
            process_red_light(new_positions)

        players = new_positions  # Update player positions

        # Draw bounding boxes
        for i, (x, y, w, h) in enumerate(players):
            color = RED if i in eliminated_players else GREEN
            pygame.draw.rect(screen, color, (x, y, w, h), 3)
            if i in eliminated_players:
                pygame.draw.line(screen, RED, (x, y), (x + w, y + h), 5)
                pygame.draw.line(screen, RED, (x + w, y), (x, y + h), 5)

    # Check for victory
    if any(y <= 50 for _, y, _, _ in players if _ not in eliminated_players) and False:
        game_state = VICTORY

    if game_state == VICTORY:
        text = FONT.render("VICTORY! Game Over!", True, (0, 255, 0))
        screen.blit(text, (WIDTH // 2 - 100, HEIGHT // 2))

    # display players on a new surface on the half right of the screen
    players_surface = pygame.Surface((WIDTH // 2, HEIGHT))
    display_players(players_surface, merge_players(players, eliminated_players))
    screen.blit(players_surface, (WIDTH // 2, 0))
    
    pygame.display.flip()

# Cleanup
cap.release()
pygame.quit()
