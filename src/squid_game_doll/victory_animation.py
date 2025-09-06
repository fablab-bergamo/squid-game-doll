"""
Victory Animation System

Handles the animated victory sequence when players win the game.
Features animated winner badge movement, scaling, and prize display.
"""

import pygame
import math
import time
from typing import List, Dict, Tuple, Optional
from .constants import (
    PLAYER_SIZE, YELLOW, GREEN, SALMON, WHITE, BLACK
)


class WinnerSprite:
    """
    Animated sprite for a winning player badge.
    
    Handles movement from current position to center screen with scaling animation.
    """
    
    def __init__(self, player_data: Dict, start_pos: Tuple[int, int], target_pos: Tuple[int, int]):
        """
        Initialize winner sprite animation.
        
        Args:
            player_data: Player information (image, id, prize amount)
            start_pos: Starting position (x, y)
            target_pos: Target center position (x, y)
        """
        self.player_data = player_data
        self.start_pos = start_pos
        self.current_pos = list(start_pos)  # Mutable for animation
        self.target_pos = target_pos
        
        # Animation properties
        self.start_scale = 1.0
        self.target_scale = 2.5  # 250% enlargement as requested
        self.current_scale = self.start_scale
        
        # Animation timing
        self.animation_duration = 4.0  # 4 seconds for slower movement
        self.start_time = time.time()
        self.is_moving = True
        self.movement_complete = False
        
        # Easing parameters for smooth animation
        self.ease_power = 2.0  # For ease-in-out effect
    
    def update(self, dt: float) -> None:
        """
        Update sprite animation position and scale.
        
        Args:
            dt: Delta time since last update
        """
        if not self.is_moving:
            return
            
        elapsed = time.time() - self.start_time
        progress = min(elapsed / self.animation_duration, 1.0)
        
        # Apply easing function (ease-in-out)
        eased_progress = self._ease_in_out(progress)
        
        # Interpolate position
        self.current_pos[0] = self.start_pos[0] + (self.target_pos[0] - self.start_pos[0]) * eased_progress
        self.current_pos[1] = self.start_pos[1] + (self.target_pos[1] - self.start_pos[1]) * eased_progress
        
        # Interpolate scale
        self.current_scale = self.start_scale + (self.target_scale - self.start_scale) * eased_progress
        
        # Check if animation is complete
        if progress >= 1.0:
            self.is_moving = False
            self.movement_complete = True
    
    def _ease_in_out(self, t: float) -> float:
        """
        Ease-in-out animation curve for smooth movement.
        
        Args:
            t: Time progress (0.0 to 1.0)
            
        Returns:
            Eased progress value
        """
        if t < 0.5:
            return self.ease_power * t * t
        else:
            return 1 - pow(-2 * t + 2, self.ease_power) / 2
    
    def get_current_size(self) -> int:
        """Get current scaled player size."""
        return int(PLAYER_SIZE * self.current_scale)
    
    def get_render_pos(self) -> Tuple[int, int]:
        """Get position adjusted for current sprite size."""
        size = self.get_current_size()
        return (
            int(self.current_pos[0] - size // 2),
            int(self.current_pos[1] - size // 2)
        )


class VictoryAnimation:
    """
    Complete victory animation system.
    
    Manages the full victory sequence: webcam fade out, winner badge animation,
    and prize amount display.
    """
    
    def __init__(self, screen_width: int, screen_height: int):
        """
        Initialize victory animation system.
        
        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Animation state
        self.winners: List[WinnerSprite] = []
        self.animation_phase = "fade_out"  # fade_out -> badges_moving -> show_prize -> complete
        self.start_time = time.time()
        
        # Phase durations
        self.fade_duration = 1.0  # 1 second fade out
        self.movement_duration = 4.0  # 4 seconds for slower badge movement
        self.prize_delay = 3.0  # 3 seconds delay before showing prize
        self.total_display_time = 6.0  # Total time to display final result
        
        # Visual effects
        self.fade_alpha = 0
        self.show_prize = False
        self.prize_alpha = 0
        
        # Background fade surface
        self.fade_surface = pygame.Surface((screen_width, screen_height))
        self.fade_surface.fill(BLACK)
        
    def start_animation(self, winners: List[Dict], current_player_positions: List[Tuple[int, int]]) -> None:
        """
        Start the victory animation with winning players.
        
        Args:
            winners: List of winner player data dictionaries
            current_player_positions: Current positions of player badges on screen
        """
        self.winners = []
        self.start_time = time.time()
        self.animation_phase = "fade_out"
        
        # Calculate target positions for winners in center
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        
        if len(winners) == 1:
            # Single winner goes to exact center
            target_positions = [(center_x, center_y)]
        else:
            # Multiple winners arranged to prevent overlaps
            # Calculate required radius based on badge size and count
            final_badge_size = PLAYER_SIZE * 2.5  # 250% scaling
            
            if len(winners) == 2:
                # Two winners: place side by side with padding
                spacing = final_badge_size * 1.2  # 20% padding between badges
                target_positions = [
                    (center_x - int(spacing // 2), center_y),
                    (center_x + int(spacing // 2), center_y)
                ]
            elif len(winners) <= 6:
                # 3-6 winners: arrange in circle with calculated radius
                # Use circumference formula to ensure no overlaps
                circumference = len(winners) * final_badge_size * 1.3  # 30% padding
                radius = max(200, int(circumference / (2 * math.pi)))  # Minimum 200px radius
                
                angle_step = 2 * math.pi / len(winners)
                target_positions = []
                
                for i in range(len(winners)):
                    angle = i * angle_step
                    target_x = center_x + int(radius * math.cos(angle))
                    target_y = center_y + int(radius * math.sin(angle))
                    target_positions.append((target_x, target_y))
            else:
                # Many winners: arrange in multiple rows
                cols = min(4, len(winners))  # Max 4 per row
                rows = (len(winners) + cols - 1) // cols  # Ceiling division
                
                spacing_x = final_badge_size * 1.2
                spacing_y = final_badge_size * 1.2
                
                # Calculate starting position to center the grid
                total_width = (cols - 1) * spacing_x
                total_height = (rows - 1) * spacing_y
                start_x = center_x - total_width // 2
                start_y = center_y - total_height // 2
                
                target_positions = []
                for i in range(len(winners)):
                    row = i // cols
                    col = i % cols
                    target_x = int(start_x + col * spacing_x)
                    target_y = int(start_y + row * spacing_y)
                    target_positions.append((target_x, target_y))
        
        # Create winner sprites
        for i, winner in enumerate(winners):
            if i < len(current_player_positions) and i < len(target_positions):
                sprite = WinnerSprite(
                    winner, 
                    current_player_positions[i], 
                    target_positions[i]
                )
                self.winners.append(sprite)
    
    def update(self, dt: float) -> None:
        """
        Update animation state and all sprites.
        
        Args:
            dt: Delta time since last update
        """
        elapsed = time.time() - self.start_time
        
        # Update animation phase
        if self.animation_phase == "fade_out":
            # Fade out webcam feed
            progress = min(elapsed / self.fade_duration, 1.0)
            self.fade_alpha = int(255 * progress)
            
            if progress >= 1.0:
                self.animation_phase = "badges_moving"
                # Start badge movement animations
                for winner in self.winners:
                    winner.start_time = time.time()
                    
        elif self.animation_phase == "badges_moving":
            # Update all winner sprites
            for winner in self.winners:
                winner.update(dt)
            
            # Check if all badges finished moving
            if all(winner.movement_complete for winner in self.winners):
                self.animation_phase = "show_prize"
                self.prize_start_time = time.time()
                
        elif self.animation_phase == "show_prize":
            # Show prize with fade in
            prize_elapsed = time.time() - self.prize_start_time
            if prize_elapsed >= self.prize_delay:
                self.show_prize = True
                fade_progress = min((prize_elapsed - self.prize_delay) / 0.5, 1.0)
                self.prize_alpha = int(255 * fade_progress)
                
                # Check if we should finish
                if prize_elapsed >= self.total_display_time:
                    self.animation_phase = "complete"
    
    def render(self, surface: pygame.Surface, webcam_surface: Optional[pygame.Surface] = None) -> None:
        """
        Render the victory animation.
        
        Args:
            surface: Main screen surface to render on (background already applied)
            webcam_surface: Not used anymore - background is handled by GameScreen
        """
        # Background is already rendered by GameScreen, no webcam handling needed
        # Just apply subtle dimming overlay to make badges more visible
        if self.animation_phase in ["badges_moving", "show_prize", "complete"] and self.fade_alpha > 0:
            # Dim the background slightly (20% opacity) to make badges pop
            dim_alpha = min(int(self.fade_alpha * 0.2), 51)  # Max 20% opacity
            self.fade_surface.set_alpha(dim_alpha)
            surface.blit(self.fade_surface, (0, 0))
        
        # Render winner badges
        if self.animation_phase in ["badges_moving", "show_prize", "complete"]:
            for winner in self.winners:
                self._render_winner_badge(surface, winner)
        
        # Render prize information
        if self.show_prize and self.animation_phase in ["show_prize", "complete"]:
            self._render_prize_info(surface)
    
    def _render_winner_badge(self, surface: pygame.Surface, winner: WinnerSprite) -> None:
        """
        Render a single winner badge with current animation state.
        
        Args:
            surface: Surface to render on
            winner: Winner sprite to render
        """
        pos = winner.get_render_pos()
        size = winner.get_current_size()
        
        # Create scaled surface for this badge with full transparency
        badge_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        badge_surface.fill((0, 0, 0, 0))  # Start completely transparent
        
        # Define diamond points (scaled)
        diamond_points = [
            (size // 2, 0),                    # Top
            (size, size // 2),                 # Right  
            (size // 2, size),                 # Bottom
            (0, size // 2),                    # Left
        ]
        
        # Create mask surface for diamond shape
        mask_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        mask_surface.fill((0, 0, 0, 0))  # Transparent background
        pygame.draw.polygon(mask_surface, (255, 255, 255, 255), diamond_points)
        
        # Scale player image and apply diamond mask
        player_img = winner.player_data["image"]
        scaled_img = pygame.transform.scale(player_img, (size, size))
        
        # Create a surface for the masked image
        masked_img = pygame.Surface((size, size), pygame.SRCALPHA)
        masked_img.fill((0, 0, 0, 0))
        
        # Apply diamond mask to player image
        masked_img.blit(scaled_img, (0, 0))
        masked_img.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        
        # Draw the masked player image
        badge_surface.blit(masked_img, (0, 0))
        
        # Draw diamond border
        border_thickness = max(2, int(8 * winner.current_scale))
        pygame.draw.polygon(badge_surface, SALMON, diamond_points, width=border_thickness)
        
        # Draw player number (scaled font)
        font_size = int(24 * winner.current_scale)
        font = pygame.font.Font(None, font_size)
        number_text = font.render(str(winner.player_data["id"]), True, YELLOW)
        number_rect = number_text.get_rect(center=(size // 2, int(size * 0.8)))
        badge_surface.blit(number_text, number_rect)
        
        # Blit the complete badge to main surface
        surface.blit(badge_surface, pos)
    
    def _render_prize_info(self, surface: pygame.Surface) -> None:
        """
        Render prize information below the winner badges.
        
        Args:
            surface: Surface to render on
        """
        if not self.winners:
            return
            
        # Calculate total prize
        total_eliminated = sum(1 for winner in self.winners if winner.player_data.get("total_eliminated", 0) > 0)
        if total_eliminated == 0:
            total_eliminated = 1  # Fallback
        
        total_prize = 100_000_000 * total_eliminated
        prize_per_winner = total_prize // len(self.winners)
        
        # Create prize text
        font_large = pygame.font.Font(None, 72)
        font_medium = pygame.font.Font(None, 48)
        
        # Victory text - positioned above the badges
        victory_text = font_large.render("VITTORIA!", True, GREEN)
        victory_rect = victory_text.get_rect(center=(self.screen_width // 2, self.screen_height // 2 - 200))
        
        # Prize amount text - positioned above the badges, below victory text
        prize_text = font_medium.render(f"Ogni vincitore: ₩ {prize_per_winner:,}", True, YELLOW)
        prize_rect = prize_text.get_rect(center=(self.screen_width // 2, self.screen_height // 2 - 150))
        
        # Apply alpha if fading in
        if self.prize_alpha < 255:
            victory_text.set_alpha(self.prize_alpha)
            prize_text.set_alpha(self.prize_alpha)
        
        surface.blit(victory_text, victory_rect)
        surface.blit(prize_text, prize_rect)
    
    def is_complete(self) -> bool:
        """Check if the animation sequence is complete."""
        return self.animation_phase == "complete"
    
    def get_phase(self) -> str:
        """Get current animation phase."""
        return self.animation_phase