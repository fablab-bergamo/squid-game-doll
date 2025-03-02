import pygame
import cv2
import numpy as np
import random
import time
import os
from display_players import display_players, load_player_image
from players_tracker import PlayerTracker, Player
import mediapipe as mp


class SquidGame:
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    WIDTH, HEIGHT = 1600, 1200
    FONT_COLOR = RED

    def __init__(self):
        pygame.init()
        # Constants
        self.FONT = pygame.font.Font(None, 36)
        self.FONT_FINE = pygame.font.Font(None, 85)

        # Colors
        self.ROOT = os.path.dirname(__file__)
        self.previous_time = time.time()
        self.previous_positions = []
        self.tracker = PlayerTracker()
        self.FAKE = False
        self.face_detector = mp.solutions.face_detection.FaceDetection(
            min_detection_confidence=0.5
        )  # Mediapipe Face Detector

    def __del__(self):
        pygame.quit()

    def extract_face(self, frame, bbox):
        """
        Extracts a face from a given person's bounding box.
        Args:
            frame (numpy.ndarray): The input frame.
            bbox (tuple): Bounding box (x1, y1, x2, y2) of the detected player.
        Returns:
            face_crop (numpy.ndarray or None): Cropped face if detected, otherwise None.
        """
        x1, y1, x2, y2 = bbox

        # Crop the person from the frame
        person_crop = frame[y1:y2, x1:x2]

        if person_crop.size == 0:
            return None

        # Convert to RGB for Mediapipe
        rgb_face = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)

        # Detect faces
        results = self.face_detector.process(rgb_face)

        if results.detections:
            for detection in results.detections:
                # Get face bounding box relative to the cropped person
                bboxC = detection.location_data.relative_bounding_box
                fx, fy, fw, fh = bboxC.xmin, bboxC.ymin, bboxC.width, bboxC.height

                # Convert relative coordinates to absolute
                h, w, _ = person_crop.shape
                fx, fy, fw, fh = int(fx * w), int(fy * h), int(fw * w), int(fh * h)

                # Extract face
                face_crop = person_crop[fy : fy + fh, fx : fx + fw]

                return face_crop

        return None

    def detect_players(self, frame, num_players: int) -> list:
        """Simulate an external detection system returning bounding boxes."""
        if self.FAKE:
            if time.time() - self.previous_time > 1:
                self.previous_time = time.time()
                self.previous_positions = [
                    (random.randint(100, 700), random.randint(100, 500), 80, 120)
                    for _ in range(num_players)
                ]
            return self.previous_positions

        players = self.tracker.process_frame(frame)
        return players

    def draw_overlay(self, screen, game_state):
        """Display game status."""
        text = self.FONT.render(f"Phase: {game_state}", True, self.FONT_COLOR)
        screen.blit(text, (20, 20))

    def merge_players(self, players, eliminated) -> list:
        # Creiamo un dizionario per mantenere giocatori unici con il loro stato
        risultato = []
        cpt = 1
        # Aggiungiamo i giocatori dalla lista attiva/eliminata
        for player in players:
            risultato.append(
                {
                    "number": cpt,
                    "active": True if player not in eliminated else False,
                    "image": load_player_image(self.ROOT + "/media/sample_player.jpg"),
                    "rectangle": player.get_rect(),
                    "id": player.id,
                }
            )
            cpt += 1

        # Aggiungiamo i giocatori dalla lista eliminata, forzando lo stato a False
        for player in eliminated:
            for p in risultato:
                if p["id"] == player.id:
                    p["active"] = False

        return risultato

    def game_loop(self):
        # Initialize screen
        screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Squid Game - Green Light Red Light")

        # Load sounds
        intro_sound = pygame.mixer.Sound(self.ROOT + "/media/intro.mp3")
        green_sound = pygame.mixer.Sound(self.ROOT + "/media/green_light.mp3")
        # 무궁화 꽃이 피었습니다
        red_sound = pygame.mixer.Sound(self.ROOT + "/media/red_light.mp3")
        eliminate_sound = pygame.mixer.Sound(self.ROOT + "/media/eliminated.mp3")

        # add loading screen picture during intro sound
        loading_screen = pygame.image.load(self.ROOT + "/media/loading_screen.webp")
        screen.blit(loading_screen, (0, 0))
        pygame.display.flip()
        intro_sound.play()

        os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

        # OpenCV webcam setup
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        while pygame.mixer.get_busy():
            pygame.event.get()

        # Game States
        INIT, GREEN_LIGHT, RED_LIGHT, VICTORY, GAMEOVER = (
            "INIT",
            "GREEN_LIGHT",
            "RED_LIGHT",
            "VICTORY",
            "GAME OVER",
        )
        game_state = INIT

        # Simulated external player detection (bounding boxes format: [x, y, w, h])
        players = []
        eliminated_players = set()

        # Timing for Red/Green Light
        last_switch_time = time.time()
        green_light = True

        screen.fill((0, 0, 0))

        delay_s = random.randint(1, 5)

        # Game Loop
        running = True
        while running:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert OpenCV BGR to RGB for PyGame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.rot90(frame)  # Rotate to match PyGame coordinates
            frame = cv2.resize(frame, (self.WIDTH // 2, self.HEIGHT))
            frame_surface = pygame.surfarray.make_surface(frame)
            screen.blit(frame_surface, (0, 0))  # Show webcam feed

            # Handle Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Game Logic
            if game_state == INIT:
                players = self.detect_players(frame, 5)
                self.draw_overlay(screen, game_state)
                text = self.FONT.render("Waiting for players...", True, self.FONT_COLOR)
                screen.blit(text, (self.WIDTH // 2 - 100, self.HEIGHT // 2))
                while len(players) < 1:
                    pygame.display.flip()
                    time.sleep(0.5)
                    ret, frame = cap.read()
                    if not ret:
                        break
                    players = self.detect_players(frame, 5)

                game_state = GREEN_LIGHT
                green_sound.play()

            elif game_state in [GREEN_LIGHT, RED_LIGHT]:
                # Switch phase randomly (1-5 seconds)
                if time.time() - last_switch_time > delay_s:
                    green_light = not green_light
                    last_switch_time = time.time()
                    game_state = GREEN_LIGHT if green_light else RED_LIGHT
                    (red_sound if green_light else green_sound).stop()
                    (green_sound if green_light else red_sound).play()
                    delay_s = random.randint(1, 5)

                # New player positions (simulating new detections)
                players = self.detect_players(frame, len(players))

                if not green_light:
                    for player in players:
                        if player.has_moved():
                            eliminated_players.add(player)
                            eliminate_sound.play()

                # Draw bounding boxes
                for player in players:
                    color = self.RED if player in eliminated_players else self.GREEN
                    x, y, w, h = player.get_rect()
                    pygame.draw.rect(screen, color, (x, y, w, h), 3)
                    if player in eliminated_players:
                        pygame.draw.line(screen, self.RED, (x, y), (x + w, y + h), 5)
                        pygame.draw.line(screen, self.RED, (x + w, y), (x, y + h), 5)

            # Check for victory

            # Verifica se ci sono ancora giocatori attivi
            if len(eliminated_players) == len(players) and len(players) > 0:
                game_state = GAMEOVER

            # display players on a new surface on the half right of the screen
            players_surface = pygame.Surface((self.WIDTH // 2, self.HEIGHT))
            display_players(
                players_surface, self.merge_players(players, eliminated_players)
            )
            screen.blit(players_surface, (self.WIDTH // 2, 0))

            if game_state == GAMEOVER:
                text = self.FONT_FINE.render(
                    "GAME OVER! No vincitori...", True, (255, 0, 0)
                )
                screen.blit(text, (self.WIDTH // 2 - 300, self.HEIGHT - 250))
                players = self.detect_players(frame, len(players))
                # Draw bounding boxes
                for player in players:
                    color = self.RED if player in eliminated_players else self.GREEN
                    x, y, w, h = player.get_rect()
                    pygame.draw.rect(screen, color, (x, y, w, h), 3)
                    if player in eliminated_players:
                        pygame.draw.line(screen, self.RED, (x, y), (x + w, y + h), 5)
                        pygame.draw.line(screen, self.RED, (x + w, y), (x, y + h), 5)

            if game_state == VICTORY:
                text = self.FONT_FINE.render("VICTORY!", True, (0, 255, 0))
                screen.blit(text, (self.WIDTH // 2 - 200, self.HEIGHT - 250))

            pygame.display.flip()
            pygame.time.delay(100)

        # Cleanup
        cap.release()


if __name__ == "__main__":
    game = SquidGame()
    game.game_loop()
