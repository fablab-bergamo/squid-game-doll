# Laser Finder Integration Plan for Main Game Loop

## Current State Analysis

**Note**: All coordinate parameters passed to the shooter should be normalized to 0...1 range based on camera area width and height for proper servo positioning.

### Existing Elimination Flow

1. **RED_LIGHT phase**: Movement detection active after 0.5s grace period
2. **Player violation detected**: `player.has_moved()` or `player.has_expired()`
3. **Audio feedback**: Elimination sound plays immediately
4. **Current laser sequence**: 5-second targeting with incomplete `LaserTracker.track_and_shoot()`

### Current Laser System Status

- **LaserShooter**: ✅ Complete (ESP32 communication, PID control, servo positioning)
- **LaserTracker**: ⚠️ Incomplete (`track_and_shoot()` only turns laser on)
- **LaserFinder**: ✅ Complete (Hough circles detection for laser dot)
- **LaserFinderNN**: ✅ New neural network implementation ready

## Integration Architecture

### 1. Enhanced LaserTracker Implementation

**Replace current incomplete `track_and_shoot()` method with:**

```python
def track_and_shoot_with_nn(self, target_bbox: tuple, frame_width: int, frame_height: int) -> bool:
    """
    Complete laser targeting sequence using LaserFinderNN
    
    Args:
        target_bbox: (x1, y1, x2, y2) of eliminated player
        frame_width: Camera frame width for coordinate normalization
        frame_height: Camera frame height for coordinate normalization
        
    Returns:
        bool: True if laser successfully positioned on target
    """
    # Phase 1: Initialize laser finder and enable laser
    laser_finder_nn = LaserFinderNN()
    self.shooter.set_laser(True)
    
    # Phase 2: Timeout-based targeting loop
    TIMEOUT_SECONDS = 10  # Maximum targeting time
    TARGET_ACCURACY = 20  # pixels
    start_time = time.time()
    
    while (time.time() - start_time < TIMEOUT_SECONDS):
        # Get current frame from camera via game loop
        if self.last_frame is None:
            pygame.time.delay(50)  # Wait 50ms for next frame
            continue
            
        # Detect current laser position
        laser_coord, annotated_frame = laser_finder_nn.find_laser(self.last_frame)
        
        if not laser_finder_nn.laser_found():
            # Laser not detected - continue search
            pygame.time.delay(50)
            continue
        
        # Calculate target center - aim for upper torso (chest area)
        target_center = self._calculate_upper_body_target(target_bbox)
        
        # Check if laser is within acceptable accuracy
        if self._is_laser_on_target(laser_coord, target_center, TARGET_ACCURACY):
            # SUCCESS: Laser positioned on target
            self._shot_done = True
            return True
        
        # Normalize coordinates for shooter (0...1 range)
        laser_normalized = (laser_coord[0] / frame_width, laser_coord[1] / frame_height)
        target_normalized = (target_center[0] / frame_width, target_center[1] / frame_height)
        
        # Adjust laser position using PID control
        error = self.shooter.track_target_PID(laser_normalized, target_normalized)
        
        # Small delay for servo movement
        pygame.time.delay(200)  # 200ms delay for servo positioning
        
    # TIMEOUT: Could not position laser accurately
    return False

def _calculate_upper_body_target(self, bbox: tuple) -> tuple:
    """Calculate target point in upper body area (chest/torso)"""
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) // 2
    # Target upper third of bounding box for chest area
    target_y = y1 + int((y2 - y1) * 0.3)
    return (center_x, target_y)
```

### 2. Game Loop Integration Points

**Modified elimination sequence in `squid_game.py`:**

```python
# In RED_LIGHT phase elimination logic
if player.has_moved(settings) and not player.is_eliminated():
    player.set_eliminated(True)
    self.eliminate_sound.play()
    
    # Enhanced laser targeting sequence
    if not self.no_tracker and self.shooter.is_laser_enabled():
        success = self._execute_laser_elimination(player)
        if success:
            self.gunshot_sound.play()  # Play gunshot on successful targeting
        # Always switch off laser after targeting attempt
        self.shooter.set_laser(False)
```

**New method for complete laser elimination:**

```python
def _execute_laser_elimination(self, player: Player) -> bool:
    """
    Execute complete laser elimination sequence for a player
    
    Args:
        player: The eliminated player to target
        
    Returns:
        bool: True if laser successfully targeted player
    """
    # Get player bounding box for targeting
    target_bbox = player.get_bbox()  # (x1, y1, x2, y2)
    
    # Start enhanced laser tracking
    self.laser_tracker.set_target_bbox(target_bbox)
    self.laser_tracker.start_enhanced_targeting()
    
    # Monitor targeting progress with visual feedback
    TIMEOUT_SECONDS = 15  # Maximum time for targeting
    start_time = time.time()
    
    while (time.time() - start_time < TIMEOUT_SECONDS):
        # Update frame for laser detection
        ret, webcam_frame = self.cam.read()
        if ret:
            self.laser_tracker.update_frame(webcam_frame)
            
        # Check if targeting complete
        if self.laser_tracker.shot_complete():
            return True
            
        # Update display with targeting progress
        self._render_targeting_display(player, self.laser_tracker.get_progress())
        
        clock.tick(5)  # 5 FPS during targeting
    
    # Timeout - stop laser
    self.laser_tracker.stop()
    return False
```

### 3. Laser Confirmation Mechanism

**Target Validation Strategy:**

1. **Bounding Box Intersection**: Laser coordinates must be within player's bounding box
2. **Center Proximity**: Prioritize laser placement near player center (chest area)
3. **Stability Check**: Laser must remain on target for 0.5 seconds (confidence)

```python
def _is_laser_on_target(self, laser_coord: tuple, target_bbox: tuple, accuracy: int) -> bool:
    """
    Check if laser is positioned within the target player's bounding box
    
    Args:
        laser_coord: (x, y) laser position
        target_bbox: (x1, y1, x2, y2) player bounding box
        accuracy: Maximum allowed pixel error
        
    Returns:
        bool: True if laser is positioned on target
    """
    x1, y1, x2, y2 = target_bbox
    laser_x, laser_y = laser_coord
    
    # Check if laser is within expanded bounding box (with accuracy tolerance)
    in_x_range = (x1 - accuracy) <= laser_x <= (x2 + accuracy)
    in_y_range = (y1 - accuracy) <= laser_y <= (y2 + accuracy)
    
    return in_x_range and in_y_range
```

### 4. Error Handling & Timeout Strategies

**Timeout Conditions:**

- **Maximum targeting time**: 15 seconds per player
- **Laser detection failure**: 5 consecutive frames without laser detection
- **Servo communication loss**: ESP32 connection timeout

**Fallback Strategies:**

1. **Laser not detected**: Continue with audio elimination only
2. **Targeting timeout**: Mark elimination complete, move to next player
3. **Hardware failure**: Disable laser system, continue game with audio feedback

**Error Recovery:**

```python
def _handle_laser_targeting_error(self, error_type: str, player: Player):
    """Handle various laser targeting errors gracefully"""
    logger.warning(f"Laser targeting error: {error_type} for player {player.get_id()}")
    
    if error_type == "laser_not_detected":
        # Continue targeting for a few more seconds
        pass
    elif error_type == "hardware_timeout":
        # Disable laser system for remainder of game
        self.shooter = None
        self.laser_tracker = None
    elif error_type == "targeting_timeout":
        # Mark as complete and continue
        player.set_elimination_complete(True)
```

### 5. Visual Feedback Enhancements

**During Targeting Display:**

- Show real-time laser detection with crosshair
- Display targeting progress bar
- Highlight target player with red outline
- Show laser accuracy distance in pixels
- Add crosshairs overlay to eliminated player badges for clear targeting indication

### 6. Performance Considerations

**Optimization Strategies:**

- **Reduced frame rate**: 5 FPS during targeting (vs 15 FPS normal gameplay)
- **Neural network sharing**: Single LaserFinderNN instance for all eliminations
- **Frame buffering**: Skip frames if processing lags behind
- **Early termination**: Stop targeting once accuracy achieved

## Implementation Priority

1. **Phase 1**: Enhance LaserTracker with complete targeting logic
2. **Phase 2**: Integrate neural network laser detection
3. **Phase 3**: Add visual feedback and progress display  
4. **Phase 4**: Implement error handling and recovery
5. **Phase 5**: Performance optimization and testing

This plan provides a complete laser targeting system that confirms laser positioning within eliminated player bounding boxes while maintaining game flow and providing appropriate fallbacks for error conditions.
