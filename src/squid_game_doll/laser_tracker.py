import cv2
from threading import Thread
from typing import Tuple
from loguru import logger
from .laser_finder import LaserFinder
from .laser_finder_nn import LaserFinderNN
from .laser_shooter import LaserShooter


class LaserTracker:
    def __init__(self, shooter: LaserShooter, laser_finder=None):
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
        if player != self.target:
            self._shot_done = False

        self.target = player

    def start(self):
        if self.thread.is_alive():
            self.shall_run = False
            self.thread.join()
            logger.debug("start: thread joined")

        self.thread = Thread(target=self.track_and_shoot)
        self.thread.start()

    def update_frame(self, webcam: cv2.UMat, nn_frame: cv2.UMat = None) -> None:
        self.last_frame = webcam.copy()
        self.last_nn_frame = nn_frame.copy() if nn_frame is not None else None

    def stop(self):
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
        return self._shot_done

    def get_picture(self) -> cv2.UMat:
        return self._picture
