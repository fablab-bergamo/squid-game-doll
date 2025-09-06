# Native 0...1 Floating Point Coordinate System Rewrite

## Overview

Complete system redesign to use normalized 0...1 floating point coordinates throughout the entire laser targeting pipeline, from computer vision detection to ESP32 servo control.

## System Architecture Changes

### 1. LaserFinderNN Modifications

**Current Output**: Pixel coordinates (e.g., (320, 240) for 640x480 image)
**New Output**: Normalized coordinates (e.g., (0.5, 0.5) for center of image)

```python
class LaserFinderNN:
    def __init__(self, model_path: str = "yolov5l6_e200_b8_tvt302010_laser_v5.pt"):
        # Existing initialization
        self.output_normalized = True  # New flag for coordinate format
    
    def find_laser(self, img: cv2.UMat, rects: list = None) -> Tuple[Optional[Tuple[float, float]], Optional[cv2.UMat]]:
        """
        Find laser and return normalized coordinates (0...1 range)
        
        Returns:
            Tuple of (normalized_coordinates, output_image)
            normalized_coordinates: (x_norm, y_norm) where 0.0 <= x_norm, y_norm <= 1.0
        """
        if self.model is None:
            return (None, None)
        
        try:
            # Convert UMat to numpy if needed
            if isinstance(img, cv2.UMat):
                img_np = cv2.UMat.get(img)
            else:
                img_np = img
                
            frame_height, frame_width = img_np.shape[:2]
            
            # Run inference (existing logic)
            results = self.model(img_np)
            
            # Process results with normalization
            if results.xyxy[0] is not None and len(results.xyxy[0]) > 0:
                predictions = results.xyxy[0].cpu().numpy()
                
                detections = []
                output_image = img_np.copy()
                
                for pred in predictions:
                    x1, y1, x2, y2, conf, class_id = pred
                    class_name = self.model.names[int(class_id)]
                    
                    # Calculate center in pixels
                    center_x_px = int((x1 + x2) / 2)
                    center_y_px = int((y1 + y2) / 2)
                    
                    # NORMALIZE TO 0...1 RANGE
                    center_x_norm = center_x_px / frame_width
                    center_y_norm = center_y_px / frame_height
                    
                    detection = {
                        'center_normalized': (center_x_norm, center_y_norm),
                        'center_pixels': (center_x_px, center_y_px),  # Keep for visualization
                        'bbox_normalized': (x1/frame_width, y1/frame_height, x2/frame_width, y2/frame_height),
                        'bbox_pixels': (int(x1), int(y1), int(x2), int(y2)),
                        'confidence': float(conf),
                        'class_name': class_name
                    }
                    detections.append(detection)
                    
                    # Draw bounding box using pixel coordinates for visualization
                    cv2.rectangle(output_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.circle(output_image, (center_x_px, center_y_px), 5, (0, 0, 255), -1)
                    
                    # Draw label
                    label = f"{class_name}: {conf:.2f} ({center_x_norm:.3f},{center_y_norm:.3f})"
                    cv2.putText(output_image, label, (int(x1), int(y1) - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                if detections:
                    # Select best detection (highest confidence)
                    best_detection = max(detections, key=lambda d: d['confidence'])
                    self.laser_coord = best_detection['center_normalized']  # NORMALIZED
                    self.prev_detections = detections
                    
                    return (self.laser_coord, output_image)
            
            # No detections found
            self.laser_coord = None
            return (None, None)
                
        except Exception as e:
            logger.error(f"Error during YOLOv5 inference: {e}")
            self.laser_coord = None
            return (None, None)
    
    def get_laser_coord(self) -> Optional[Tuple[float, float]]:
        """Get normalized laser coordinates (0...1 range)"""
        return self.laser_coord
```

### 2. LaserShooter Complete Rewrite

**New Philosophy**: Direct mapping from normalized coordinates to servo angles

```python
class LaserShooter:
    def __init__(self, ipaddress: str, deadband_norm: float = 0.02, max_frequency_hz: int = 10, enable_laser: bool = True):
        """
        Initialize LaserShooter with normalized coordinate system
        
        Args:
            deadband_norm: Deadband in normalized coordinates (0...1 range), e.g., 0.02 = 2% of frame
        """
        self._is_online = False
        self.ip_address = ipaddress
        self.port = 15555
        self.aliensocket: socket = None
        self.last_sent: int = 0
        
        # NORMALIZED COORDINATE SYSTEM
        self.deadband_norm: float = deadband_norm  # 0...1 range
        self.min_period_S: float = 1.0 / max_frequency_hz
        
        # Get servo limits from ESP32
        self.limits: tuple = self.get_limits()  # Returns ((H_MIN, H_MAX), (V_MIN, V_MAX))
        
        # Initialize PID with normalized coordinates
        self.pid_ok: bool = self.init_PID_normalized()
        self._enable_laser = enable_laser
        
        # Servo angle ranges for direct mapping
        if self.limits:
            self.h_min, self.h_max = self.limits[0]  # e.g., (30, 150)
            self.v_min, self.v_max = self.limits[1]  # e.g., (0, 120)
            self.h_range = self.h_max - self.h_min   # e.g., 120 degrees
            self.v_range = self.v_max - self.v_min   # e.g., 120 degrees
            
            # Center positions in servo angles
            self.h_center = self.h_min + (self.h_range / 2)  # e.g., 90 degrees
            self.v_center = self.v_min + (self.v_range / 2)  # e.g., 60 degrees
    
    def init_PID_normalized(self) -> bool:
        """Initialize PID controllers for normalized coordinate system"""
        if self.limits is None:
            self.limits = self.get_limits()
        
        if self.limits is not None:
            # PID tuned for normalized coordinates (0...1 input range)
            # Higher gains needed since input errors are much smaller
            k_p = 120.0  # Proportional gain - maps normalized error to servo angle range
            k_i = 72.0   # Integral gain
            k_d = 36.0   # Derivative gain
            
            # PID output limits are servo angle ranges
            self.pid_v = PID(
                k_p, k_i, k_d,
                setpoint=0,
                output_limits=(self.v_min, self.v_max),
                starting_output=self.v_center
            )
            
            self.pid_h = PID(
                k_p, k_i, k_d,
                setpoint=0, 
                output_limits=(self.h_min, self.h_max),
                starting_output=self.h_center
            )
            
            self.pid_h.sample_time = self.min_period_S
            self.pid_v.sample_time = self.min_period_S
            
            # Initialize servos to center position
            self.send_angles_normalized(0.5, 0.5)  # Center = (0.5, 0.5) normalized
            
            self.prev_output_h = self.h_center
            self.prev_output_v = self.v_center
            return True
        
        logger.error("PID initialization failed - could not get servo limits")
        return False
    
    def normalized_to_servo_angles(self, x_norm: float, y_norm: float) -> tuple[float, float]:
        """
        Convert normalized coordinates (0...1) directly to servo angles
        
        Args:
            x_norm: Horizontal position (0.0 = left, 1.0 = right)
            y_norm: Vertical position (0.0 = top, 1.0 = bottom)
            
        Returns:
            (h_angle, v_angle): Servo angles in degrees
        """
        # Clamp to valid range
        x_norm = max(0.0, min(1.0, x_norm))
        y_norm = max(0.0, min(1.0, y_norm))
        
        # Direct linear mapping to servo ranges
        h_angle = self.h_min + (x_norm * self.h_range)
        v_angle = self.v_min + (y_norm * self.v_range)
        
        return (h_angle, v_angle)
    
    def servo_angles_to_normalized(self, h_angle: float, v_angle: float) -> tuple[float, float]:
        """
        Convert servo angles back to normalized coordinates
        
        Returns:
            (x_norm, y_norm): Normalized coordinates (0...1 range)
        """
        x_norm = (h_angle - self.h_min) / self.h_range
        y_norm = (v_angle - self.v_min) / self.v_range
        
        return (x_norm, y_norm)
    
    def track_target_normalized(self, laser_norm: tuple[float, float], target_norm: tuple[float, float]) -> float:
        """
        Track target using normalized coordinates (0...1 range) with PID control
        
        Args:
            laser_norm: Current laser position (x_norm, y_norm) in 0...1 range
            target_norm: Target position (x_norm, y_norm) in 0...1 range
            
        Returns:
            float: Positioning error in normalized distance
        """
        RATE_OF_CHANGE_DEG = 10.0  # Maximum servo angle change per update
        
        if not self.pid_ok:
            self.pid_ok = self.init_PID_normalized()
            if not self.pid_ok:
                logger.error("PID not initialized")
                return 0.0
        
        if target_norm is None or laser_norm is None:
            return 0.0
        
        # Calculate normalized errors
        horizontal_error = target_norm[0] - laser_norm[0]  # -1.0 to +1.0 range
        vertical_error = target_norm[1] - laser_norm[1]    # -1.0 to +1.0 range
        
        # Calculate normalized distance error
        normalized_distance = sqrt(horizontal_error**2 + vertical_error**2)
        
        # Check deadband in normalized coordinates
        if normalized_distance < self.deadband_norm:
            logger.debug(f"Target reached within deadband: {normalized_distance:.4f} < {self.deadband_norm:.4f}")
            return normalized_distance
        
        # Scale errors by servo ranges for PID input
        horizontal_error_scaled = horizontal_error * self.h_range
        vertical_error_scaled = vertical_error * self.v_range
        
        # Run PID controllers
        output_h = self.pid_h(horizontal_error_scaled)
        output_v = self.pid_v(vertical_error_scaled)
        
        # Apply rate limiting to prevent jerky movements
        if abs(output_h - self.prev_output_h) > RATE_OF_CHANGE_DEG:
            logger.debug(f"Rate limiting H: {output_h:.1f} -> {RATE_OF_CHANGE_DEG:.1f} deg/step")
            if output_h > self.prev_output_h:
                output_h = self.prev_output_h + RATE_OF_CHANGE_DEG
            else:
                output_h = self.prev_output_h - RATE_OF_CHANGE_DEG
        
        if abs(output_v - self.prev_output_v) > RATE_OF_CHANGE_DEG:
            logger.debug(f"Rate limiting V: {output_v:.1f} -> {RATE_OF_CHANGE_DEG:.1f} deg/step")
            if output_v > self.prev_output_v:
                output_v = self.prev_output_v + RATE_OF_CHANGE_DEG
            else:
                output_v = self.prev_output_v - RATE_OF_CHANGE_DEG
        
        # Send angles to ESP32 if changed
        if output_h != self.prev_output_h or output_v != self.prev_output_v:
            if self.send_angles((output_h, output_v)):
                self.prev_output_h = output_h
                self.prev_output_v = output_v
                logger.debug(f"Servo update: H={output_h:.1f}°, V={output_v:.1f}° | Error: ({horizontal_error:.3f}, {vertical_error:.3f}) norm")
        
        return normalized_distance
    
    def send_angles_normalized(self, x_norm: float, y_norm: float) -> bool:
        """Send normalized coordinates to ESP32 (converted to servo angles)"""
        h_angle, v_angle = self.normalized_to_servo_angles(x_norm, y_norm)
        return self.send_angles((h_angle, v_angle))
    
    def get_current_position_normalized(self) -> tuple[float, float]:
        """Get current servo position as normalized coordinates"""
        angles = self.get_angles()  # Returns (h_angle, v_angle) from ESP32
        if angles:
            return self.servo_angles_to_normalized(angles[0], angles[1])
        return (0.5, 0.5)  # Default to center if unable to read
    
    # Keep existing methods for ESP32 communication (unchanged)
    def send_angles(self, angles: tuple) -> bool:
        """Send servo angles directly to ESP32 (existing implementation)"""
        # Existing implementation remains the same
        # ... (all existing ESP32 communication code)
```

### 3. ESP32 Code Modifications

**Key Change**: ESP32 receives servo angles (no change needed) but we can optionally add normalized coordinate support.

#### Option A: No ESP32 Changes (Recommended)
Keep ESP32 as-is since LaserShooter handles the conversion from normalized coordinates to servo angles.

#### Option B: ESP32 Native Normalized Support
Add normalized coordinate handling directly in ESP32:

```python
# esp32/tracker.py additions

# Add normalized coordinate mapping constants
NORM_TO_H_MIN = 30    # H servo range: 30-150 degrees  
NORM_TO_H_MAX = 150
NORM_TO_V_MIN = 0     # V servo range: 0-120 degrees
NORM_TO_V_MAX = 120

def normalize_to_angles(x_norm, y_norm):
    """Convert normalized coordinates (0.0-1.0) to servo angles"""
    # Clamp input values
    x_norm = max(0.0, min(1.0, x_norm))
    y_norm = max(0.0, min(1.0, y_norm))
    
    # Linear mapping to servo ranges
    h_angle = NORM_TO_H_MIN + (x_norm * (NORM_TO_H_MAX - NORM_TO_H_MIN))
    v_angle = NORM_TO_V_MIN + (y_norm * (NORM_TO_V_MAX - NORM_TO_V_MIN))
    
    return (h_angle, v_angle)

async def handle_client(reader, writer):
    """Enhanced client handler with normalized coordinate support"""
    global target_coord, test_mov, force_off, laser, shutdown_event, head_pos, eyes_on
    
    # ... existing code ...
    
    if request.startswith("("):
        try:
            coords = eval(request)
            
            # Check if coordinates are normalized (0.0-1.0) or servo angles
            if (isinstance(coords[0], float) and isinstance(coords[1], float) and 
                0.0 <= coords[0] <= 1.0 and 0.0 <= coords[1] <= 1.0):
                # Normalized coordinates - convert to servo angles
                target_coord = normalize_to_angles(coords[0], coords[1])
                print(f"Normalized input ({coords[0]:.3f}, {coords[1]:.3f}) -> angles ({target_coord[0]:.1f}, {target_coord[1]:.1f})")
            else:
                # Direct servo angles (existing behavior)
                target_coord = coords
                print(f"Direct angle input: ({target_coord[0]:.1f}, {target_coord[1]:.1f})")
                
            response = "1"
        except Exception as e:
            print(f"Error updating target coordinates: {e}")
            response = "0"
    
    elif request.startswith("norm("):
        # Explicit normalized coordinate command: norm(0.5, 0.3)
        try:
            coords_str = request[5:-1]  # Remove "norm(" and ")"
            x_norm, y_norm = map(float, coords_str.split(','))
            target_coord = normalize_to_angles(x_norm, y_norm)
            print(f"Explicit normalized: ({x_norm:.3f}, {y_norm:.3f}) -> angles ({target_coord[0]:.1f}, {target_coord[1]:.1f})")
            response = "1"
        except Exception as e:
            print(f"Error parsing normalized coordinates: {e}")
            response = "0"
    
    # ... rest of existing handler code ...
```

### 4. LaserTracker Integration

**Complete rewrite for normalized coordinate system:**

```python
class LaserTracker:
    def __init__(self, shooter: LaserShooter):
        self.shooter: LaserShooter = shooter
        self.laser_finder_nn: LaserFinderNN = None
        self.target_normalized: tuple[float, float] = (0.5, 0.5)  # Center
        self._shot_done = False
        self.shall_run = False
        self.last_frame: cv2.UMat = None
        self.targeting_accuracy: float = 0.02  # 2% of frame size
        self.max_targeting_time: float = 10.0  # seconds
        
    def set_target_from_bbox(self, bbox_pixels: tuple[int, int, int, int], frame_width: int, frame_height: int):
        """Convert player bounding box to normalized target coordinates"""
        x1, y1, x2, y2 = bbox_pixels
        
        # Calculate target center (chest area - upper third of bbox)
        center_x_px = (x1 + x2) // 2
        target_y_px = y1 + int((y2 - y1) * 0.3)  # Upper torso
        
        # Normalize to 0...1 range
        self.target_normalized = (
            center_x_px / frame_width,
            target_y_px / frame_height
        )
        
        logger.info(f"Target set: pixel ({center_x_px}, {target_y_px}) -> normalized ({self.target_normalized[0]:.3f}, {self.target_normalized[1]:.3f})")
    
    def track_and_shoot_normalized(self) -> bool:
        """
        Complete laser targeting sequence using normalized coordinates
        
        Returns:
            bool: True if laser successfully positioned on target
        """
        logger.info("Starting normalized laser tracking sequence")
        
        # Initialize laser finder
        if self.laser_finder_nn is None:
            self.laser_finder_nn = LaserFinderNN()
        
        # Enable laser
        self.shooter.set_laser(True)
        
        start_time = time.time()
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        self.shall_run = True
        
        while self.shall_run and (time.time() - start_time < self.max_targeting_time):
            # Get current frame
            if self.last_frame is None:
                pygame.time.delay(50)
                consecutive_failures += 1
                if consecutive_failures > max_consecutive_failures:
                    logger.warning("Too many frame acquisition failures")
                    break
                continue
            
            consecutive_failures = 0  # Reset counter
            
            # Detect laser position (returns normalized coordinates)
            laser_coord_norm, annotated_frame = self.laser_finder_nn.find_laser(self.last_frame)
            
            if not self.laser_finder_nn.laser_found():
                logger.debug("Laser not detected, continuing search...")
                pygame.time.delay(100)
                continue
            
            logger.debug(f"Laser detected at normalized position: ({laser_coord_norm[0]:.3f}, {laser_coord_norm[1]:.3f})")
            
            # Check if laser is on target
            if self._is_laser_on_target_normalized(laser_coord_norm, self.target_normalized):
                logger.info(f"SUCCESS: Laser positioned on target within {self.targeting_accuracy:.3f} normalized accuracy")
                self._shot_done = True
                return True
            
            # Adjust laser position using normalized PID control
            error_distance = self.shooter.track_target_normalized(laser_coord_norm, self.target_normalized)
            
            logger.debug(f"Targeting: laser=({laser_coord_norm[0]:.3f}, {laser_coord_norm[1]:.3f}) "
                        f"target=({self.target_normalized[0]:.3f}, {self.target_normalized[1]:.3f}) "
                        f"error={error_distance:.4f}")
            
            # Delay for servo movement
            pygame.time.delay(200)
        
        # Timeout or stopped
        elapsed_time = time.time() - start_time
        logger.warning(f"Laser targeting timeout after {elapsed_time:.1f}s")
        return False
    
    def _is_laser_on_target_normalized(self, laser_norm: tuple[float, float], target_norm: tuple[float, float]) -> bool:
        """Check if laser is within targeting accuracy of the target"""
        distance = sqrt((laser_norm[0] - target_norm[0])**2 + (laser_norm[1] - target_norm[1])**2)
        return distance <= self.targeting_accuracy
    
    def start_targeting(self, bbox_pixels: tuple, frame_width: int, frame_height: int):
        """Start targeting sequence with automatic coordinate conversion"""
        self.set_target_from_bbox(bbox_pixels, frame_width, frame_height)
        self._shot_done = False
        
        # Run targeting in separate thread
        self.thread = Thread(target=self.track_and_shoot_normalized)
        self.thread.start()
    
    def stop(self):
        """Stop targeting and disable laser"""
        self.shall_run = False
        self.shooter.set_laser(False)
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join()
        logger.info("Laser targeting stopped")
```

### 5. Game Integration Example

**Modified elimination sequence in squid_game.py:**

```python
def _execute_laser_elimination(self, player: Player) -> bool:
    """Execute laser elimination with normalized coordinate system"""
    
    # Get current frame dimensions
    _, frame = self.cam.read()
    if frame is None:
        return False
        
    frame_height, frame_width = frame.shape[:2]
    
    # Set frame dimensions for coordinate conversion
    self.shooter.set_frame_dimensions(frame_width, frame_height)
    
    # Get player bounding box
    target_bbox = player.get_bbox()  # (x1, y1, x2, y2) in pixels
    
    logger.info(f"Starting laser elimination for player {player.get_id()}")
    logger.info(f"Frame dimensions: {frame_width}x{frame_height}")
    logger.info(f"Target bbox: {target_bbox}")
    
    # Start laser targeting
    self.laser_tracker.start_targeting(target_bbox, frame_width, frame_height)
    
    # Monitor progress
    timeout_seconds = 15.0
    start_time = time.time()
    
    while (time.time() - start_time < timeout_seconds):
        # Update frame for laser detection
        ret, webcam_frame = self.cam.read()
        if ret:
            self.laser_tracker.update_frame(webcam_frame)
        
        # Check if targeting complete
        if self.laser_tracker.shot_complete():
            logger.info("Laser targeting successful!")
            return True
        
        # Update display with targeting progress (optional)
        self._render_targeting_display(player, self.laser_tracker)
        
        pygame.time.delay(50)  # 20 FPS update rate
    
    # Timeout
    logger.warning("Laser targeting timed out")
    self.laser_tracker.stop()
    return False
```

## Performance Characteristics

### Advantages of Native 0...1 System:

1. **Resolution Independence**: Works with any camera resolution
2. **Direct Servo Mapping**: Linear relationship between coordinates and servo positions
3. **Simplified Calibration**: No pixel-to-degree conversion needed
4. **Better Precision**: Floating point precision throughout
5. **Consistent Deadband**: Targeting accuracy independent of resolution

### Computational Impact:

- **Minimal Overhead**: Simple floating point operations
- **Memory Efficient**: No need to store pixel/degree conversion factors
- **Predictable Scaling**: Linear mapping functions

### Calibration Requirements:

1. **PID Gains**: Need retuning for 0...1 input range (higher gains)
2. **Deadband**: Set in normalized coordinates (e.g., 0.02 = 2% of frame)
3. **Servo Limits**: Retrieved from ESP32, used for direct mapping

## Migration Strategy

1. **Phase 1**: Implement LaserFinderNN normalized output
2. **Phase 2**: Rewrite LaserShooter for native normalized input
3. **Phase 3**: Update LaserTracker integration
4. **Phase 4**: Game loop integration
5. **Phase 5**: PID calibration and testing
6. **Phase 6**: Optional ESP32 normalized support

This native rewrite provides a clean, consistent coordinate system throughout the entire pipeline while eliminating conversion overhead and calibration complexity.