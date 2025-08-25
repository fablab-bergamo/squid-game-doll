from typing import Optional, Tuple, List
import numpy as np
import time


class LaserCoordinateFilter:
    """
    2D coordinate smoothing filter for laser detection.
    
    This filter smooths laser detection coordinates using configurable smoothing techniques
    to reduce noise and provide stable position tracking. It provides both raw and 
    smoothed coordinates.
    
    Based on the 3D laser tracking approach from:
    https://github.com/ADVRHumanoids/nn_laser_spot_tracking/blob/master/src/laser3DTracking.cpp
    Adapted for 2D coordinate smoothing.
    """
    
    def __init__(self, 
                 smoothing_factor: float = 0.8, 
                 max_history_size: int = 10,
                 outlier_threshold: float = 50.0,
                 min_confidence_for_update: float = 0.1):
        """
        Initialize the coordinate filter.
        
        Args:
            smoothing_factor: Exponential moving average factor (0.0 to 1.0)
                            Higher values = more smoothing, slower response
                            Lower values = less smoothing, faster response
            max_history_size: Maximum number of coordinate samples to keep in history
            outlier_threshold: Maximum pixel distance from previous position to accept update
            min_confidence_for_update: Minimum detection confidence to update filter
        """
        self.smoothing_factor = max(0.0, min(1.0, smoothing_factor))
        self.max_history_size = max(1, max_history_size)
        self.outlier_threshold = outlier_threshold
        self.min_confidence_for_update = min_confidence_for_update
        
        # Filter state
        self.raw_coordinates: List[Tuple[int, int]] = []
        self.raw_confidences: List[float] = []
        self.timestamps: List[float] = []
        
        # Smoothed position state
        self.smoothed_x: Optional[float] = None
        self.smoothed_y: Optional[float] = None
        self.is_initialized = False
        
        # Outlier recovery mechanism
        self.consecutive_outliers = 0
        self.max_consecutive_outliers = 5  # Force acceptance after this many rejections
        self.recovery_mode = False
        
        # Memory persistence mechanism
        self.last_valid_update_time = None
        self.memory_timeout = 3.0  # Seconds to keep smoothed position without updates
        self.consecutive_no_detections = 0
        self.max_no_detection_frames = 30  # Frames with no detection before forgetting
        
        # Statistics
        self.total_updates = 0
        self.rejected_outliers = 0
        self.rejected_low_confidence = 0
        self.forced_acceptances = 0

    def update(self, raw_coord: Optional[Tuple[int, int]], confidence: float = 1.0) -> None:
        """
        Update filter with new raw coordinate and confidence.
        
        Args:
            raw_coord: New raw coordinate (x, y) or None if no detection
            confidence: Detection confidence (0.0 to 1.0)
        """
        current_time = time.time()
        
        if raw_coord is None:
            # No detection - increment no-detection counter but keep smoothed position in memory
            self.consecutive_no_detections += 1
            
            # Check if we should forget the smoothed position due to prolonged absence
            current_time = time.time()
            if (self.last_valid_update_time is not None and 
                current_time - self.last_valid_update_time > self.memory_timeout):
                # Too much time has passed - forget smoothed position
                self._forget_smoothed_position()
            elif self.consecutive_no_detections >= self.max_no_detection_frames:
                # Too many frames without detection - forget smoothed position  
                self._forget_smoothed_position()
            
            return
            
        x, y = raw_coord
        
        # Reject low confidence detections
        if confidence < self.min_confidence_for_update:
            self.rejected_low_confidence += 1
            return
            
        # Check for outliers (except on first detection)
        force_acceptance = False
        if self.is_initialized and self.outlier_threshold > 0:
            distance = np.sqrt((x - self.smoothed_x)**2 + (y - self.smoothed_y)**2)
            
            # Check if we should force acceptance due to too many consecutive rejections
            if distance > self.outlier_threshold:
                self.consecutive_outliers += 1
                
                if self.consecutive_outliers >= self.max_consecutive_outliers:
                    # Force acceptance - the laser has likely moved to a new location
                    force_acceptance = True
                    self.recovery_mode = True
                    self.forced_acceptances += 1
                    print(f"FILTER RECOVERY: Forcing acceptance after {self.consecutive_outliers} consecutive outliers (distance: {distance:.1f})")
                else:
                    # Normal outlier rejection
                    self.rejected_outliers += 1
                    return
            else:
                # Valid update - reset outlier counter and recovery mode
                self.consecutive_outliers = 0
                self.recovery_mode = False
        
        # Accept the detection - add to history
        self.raw_coordinates.append((int(x), int(y)))
        self.raw_confidences.append(confidence)
        self.timestamps.append(current_time)
        self.total_updates += 1
        
        # Reset no-detection counters since we have a valid update
        self.consecutive_no_detections = 0
        self.last_valid_update_time = current_time
        
        # Limit history size
        while len(self.raw_coordinates) > self.max_history_size:
            self.raw_coordinates.pop(0)
            self.raw_confidences.pop(0)
            self.timestamps.pop(0)
        
        # Update smoothed position
        if not self.is_initialized:
            # Initialize with first valid detection
            self.smoothed_x = float(x)
            self.smoothed_y = float(y) 
            self.is_initialized = True
        elif force_acceptance:
            # Recovery mode: Reset smoothed position more aggressively
            # Use higher update rate to quickly adapt to new laser position
            recovery_alpha = 0.7  # Higher alpha for faster adaptation
            self.smoothed_x = recovery_alpha * x + (1 - recovery_alpha) * self.smoothed_x
            self.smoothed_y = recovery_alpha * y + (1 - recovery_alpha) * self.smoothed_y
            # Reset consecutive outlier counter after forced acceptance
            self.consecutive_outliers = 0
        else:
            # Normal exponential moving average smoothing
            # smoothed = α * new_value + (1-α) * previous_smoothed
            alpha = 1.0 - self.smoothing_factor  # Convert to update rate
            self.smoothed_x = alpha * x + self.smoothing_factor * self.smoothed_x
            self.smoothed_y = alpha * y + self.smoothing_factor * self.smoothed_y

    def _forget_smoothed_position(self) -> None:
        """Internal method to forget the smoothed position after prolonged absence."""
        if self.last_valid_update_time is not None:
            time_diff = time.time() - self.last_valid_update_time
            print(f"FILTER MEMORY: Forgetting smoothed position after {self.consecutive_no_detections} frames / {time_diff:.1f}s without detection")
        else:
            print(f"FILTER MEMORY: Forgetting smoothed position after {self.consecutive_no_detections} frames without detection")
        self.smoothed_x = None
        self.smoothed_y = None
        self.is_initialized = False
        self.consecutive_no_detections = 0
        self.last_valid_update_time = None

    def get_raw_coordinate(self) -> Optional[Tuple[int, int]]:
        """Get the most recent raw coordinate."""
        if not self.raw_coordinates:
            return None
        return self.raw_coordinates[-1]

    def get_smoothed_coordinate(self) -> Optional[Tuple[int, int]]:
        """Get the current smoothed coordinate (persists in memory even without active detection)."""
        if not self.is_initialized or self.smoothed_x is None or self.smoothed_y is None:
            return None
        return (int(round(self.smoothed_x)), int(round(self.smoothed_y)))

    def get_smoothed_coordinate_float(self) -> Optional[Tuple[float, float]]:
        """Get the current smoothed coordinate as float values."""
        if not self.is_initialized or self.smoothed_x is None or self.smoothed_y is None:
            return None
        return (self.smoothed_x, self.smoothed_y)

    def has_detection(self) -> bool:
        """Check if filter has any valid detection (including memory)."""
        return self.is_initialized and self.smoothed_x is not None and self.smoothed_y is not None

    def get_coordinate_history(self) -> List[Tuple[int, int]]:
        """Get the full coordinate history."""
        return self.raw_coordinates.copy()

    def get_confidence_history(self) -> List[float]:
        """Get the confidence history."""
        return self.raw_confidences.copy()

    def get_latest_confidence(self) -> float:
        """Get the confidence of the most recent detection."""
        if not self.raw_confidences:
            return 0.0
        return self.raw_confidences[-1]

    def reset(self) -> None:
        """Reset the filter state."""
        self.raw_coordinates.clear()
        self.raw_confidences.clear()
        self.timestamps.clear()
        self.smoothed_x = None
        self.smoothed_y = None
        self.is_initialized = False
        self.consecutive_outliers = 0
        self.recovery_mode = False
        self.last_valid_update_time = None
        self.consecutive_no_detections = 0
        self.total_updates = 0
        self.rejected_outliers = 0
        self.rejected_low_confidence = 0
        self.forced_acceptances = 0

    def get_filter_stats(self) -> dict:
        """Get filter statistics and status."""
        avg_confidence = 0.0
        if self.raw_confidences:
            avg_confidence = sum(self.raw_confidences) / len(self.raw_confidences)
        
        time_since_update = None
        if self.last_valid_update_time is not None:
            time_since_update = time.time() - self.last_valid_update_time
        
        return {
            'is_initialized': self.is_initialized,
            'history_size': len(self.raw_coordinates),
            'total_updates': self.total_updates,
            'rejected_outliers': self.rejected_outliers,
            'rejected_low_confidence': self.rejected_low_confidence,
            'forced_acceptances': self.forced_acceptances,
            'consecutive_outliers': self.consecutive_outliers,
            'consecutive_no_detections': self.consecutive_no_detections,
            'time_since_update': time_since_update,
            'recovery_mode': self.recovery_mode,
            'has_memory': self.smoothed_x is not None and self.smoothed_y is not None,
            'average_confidence': avg_confidence,
            'smoothing_factor': self.smoothing_factor,
            'outlier_threshold': self.outlier_threshold,
            'memory_timeout': self.memory_timeout,
        }

    def set_smoothing_factor(self, smoothing_factor: float) -> None:
        """Update the smoothing factor (0.0 to 1.0)."""
        self.smoothing_factor = max(0.0, min(1.0, smoothing_factor))

    def set_outlier_threshold(self, threshold: float) -> None:
        """Update the outlier rejection threshold (pixels)."""
        self.outlier_threshold = max(0.0, threshold)

    def set_recovery_params(self, max_consecutive_outliers: int) -> None:
        """Update the recovery mechanism parameters."""
        self.max_consecutive_outliers = max(1, max_consecutive_outliers)

    def set_memory_params(self, memory_timeout: float, max_no_detection_frames: int) -> None:
        """Update the memory persistence parameters."""
        self.memory_timeout = max(0.1, memory_timeout)
        self.max_no_detection_frames = max(1, max_no_detection_frames)

    def get_velocity_estimate(self) -> Optional[Tuple[float, float]]:
        """
        Estimate current velocity based on recent coordinate history.
        
        Returns:
            Tuple of (vx, vy) in pixels per second, or None if insufficient data
        """
        if len(self.raw_coordinates) < 2 or len(self.timestamps) < 2:
            return None
            
        # Use last two positions for velocity estimate
        x1, y1 = self.raw_coordinates[-2]
        x2, y2 = self.raw_coordinates[-1]
        t1, t2 = self.timestamps[-2], self.timestamps[-1]
        
        dt = t2 - t1
        if dt <= 0:
            return None
            
        vx = (x2 - x1) / dt
        vy = (y2 - y1) / dt
        
        return (vx, vy)