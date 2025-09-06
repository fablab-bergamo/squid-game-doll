import cv2
from threading import Thread
from typing import Tuple
from loguru import logger
from .laser_finder import LaserFinder
from .laser_finder_nn import LaserFinderNN
from .laser_shooter import LaserShooter


class LaserTracker:
    """
    Laser detection and targeting coordination system.
    
    This class coordinates between laser detection (via LaserFinder/LaserFinderNN)
    and laser targeting (via LaserShooter) to create a complete laser tracking system.
    It runs in a separate thread to continuously detect and track laser positions.
    
    The LaserTracker:
    - Manages laser detection using traditional or neural network methods
    - Coordinates with ESP32-based laser shooter for targeting
    - Handles frame updates from camera systems
    - Provides thread-safe laser tracking operations
    - Supports both full-frame and optimized NN frame processing
    
    Example:
        shooter = LaserShooter("192.168.1.100")
        nn_finder = LaserFinderNN("laser_model.pt")
        tracker = LaserTracker(shooter, laser_finder=nn_finder)
        
        tracker.set_target((100, 200))  # Set target player position
        tracker.start()  # Begin tracking
    """
    
    def __init__(self, shooter: LaserShooter, laser_finder=None):
        """
        Initialize laser tracker with shooter and optional laser finder.
        
        Args:
            shooter: LaserShooter instance for controlling laser hardware
            laser_finder: Pre-loaded LaserFinder or LaserFinderNN instance.
                         If None, will use traditional LaserFinder as fallback.
        """
        self.shooter: LaserShooter = shooter
        self.laser_finder = laser_finder  # Pre-loaded laser finder
        self.thread: Thread = Thread(target=self.track_and_shoot)
        self.target: Tuple[int, int] = (0, 0)
        self._shot_done = False
        self.shall_run = False
        self.last_frame: cv2.UMat = None
        self.last_nn_frame: cv2.UMat = None
        self._picture: cv2.UMat = None

    def set_target(self, player: Tuple[int, int]) -> None:
        """Set the target player position for laser tracking.
        
        Args:
            player: Target coordinates (x, y) in image space
        """
        if player != self.target:
            self._shot_done = False

        self.target = player

    def start(self):
        """Start the laser tracking thread."""
        if self.thread.is_alive():
            self.shall_run = False
            self.thread.join()
            logger.debug("start: thread joined")

        self.thread = Thread(target=self.track_and_shoot)
        self.thread.start()

    def update_frame(self, webcam: cv2.UMat, nn_frame: cv2.UMat = None) -> None:
        """Update frames for laser detection.
        
        Args:
            webcam: Full resolution webcam frame
            nn_frame: Optional optimized frame for neural network processing
        """
        self.last_frame = webcam.copy()
        self.last_nn_frame = nn_frame.copy() if nn_frame is not None else None

    def stop(self):
        """Stop laser tracking and disable laser."""
        self.shooter.set_laser(False)
        if self.thread.is_alive():
            self.shall_run = False
            self.thread.join()
            logger.debug("stop: thread joined")

    def track_and_shoot(self) -> None:
        logger.info("track_and_shoot: thread started")
        
        # Use pre-loaded laser finder if available, otherwise fallback to traditional
        if self.laser_finder is not None and self.laser_finder.model is not None:
            finder = self.laser_finder
            use_nn = True
            logger.info("Using pre-loaded LaserFinderNN for laser detection")
        else:
            # Fallback to traditional laser finder
            finder = LaserFinder()
            use_nn = False
            logger.info("Using traditional LaserFinder (LaserFinderNN not available)")
            
        while self.shall_run:
            self.shooter.set_laser(True)
            
            if self.last_frame is not None:
                try:
                    # Pass both frames to the laser finder (NN frame preferred if available)
                    laser_coord, output_image = finder.find_laser(
                        self.last_frame, 
                        rects=[], 
                        nn_frame=self.last_nn_frame if use_nn else None
                    )
                    
                    if laser_coord is not None:
                        logger.debug(f"Laser detected at: {laser_coord}")
                        # Here we could add laser targeting logic
                        self._picture = output_image
                    
                except Exception as e:
                    logger.error(f"Error in laser detection: {e}")
            
        self.shooter.set_laser(False)

    def shot_complete(self) -> bool:
        """Check if shot is complete.
        
        Returns:
            bool: True if shot is complete, False otherwise
        """
        return self._shot_done

    def get_picture(self) -> cv2.UMat:
        """Get the last processed laser detection image.
        
        Returns:
            cv2.UMat: Last output image with detection annotations, or None
        """
        return self._picture
