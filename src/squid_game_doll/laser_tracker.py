import cv2
from threading import Thread
from .laser_finder import LaserFinder
from .laser_finder_nn import LaserFinderNN
from .laser_shooter import LaserShooter


class LaserTracker:
    def __init__(self, shooter: LaserShooter):
        self.shooter: LaserShooter = shooter
        self.thread: Thread = Thread(target=self.track_and_shoot)
        self.target: tuple[int, int] = (0, 0)
        self._shot_done = False
        self.shall_run = False
        self.last_frame: cv2.UMat = None
        self.last_nn_frame: cv2.UMat = None
        self._picture: cv2.UMat = None

    def set_target(self, player: tuple[int, int]) -> None:
        if player != self.target:
            self._shot_done = False

        self.target = player

    def start(self):
        if self.thread.is_alive():
            self.shall_run = False
            self.thread.join()
            print("start: thread joined")

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
            print("stop: thread joined")

    def track_and_shoot(self) -> None:
        print("track_and_shoot: thread started")
        try:
            # Try to use neural network laser finder first, fallback to traditional
            finder = LaserFinderNN()
            if finder.model is None:
                print("LaserFinderNN model not available, falling back to traditional LaserFinder")
                finder = LaserFinder()
                use_nn = False
            else:
                print("Using LaserFinderNN for laser detection")
                use_nn = True
        except Exception as e:
            print(f"Failed to initialize LaserFinderNN: {e}, using traditional LaserFinder")
            finder = LaserFinder()
            use_nn = False
            
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
                        print(f"Laser detected at: {laser_coord}")
                        # Here we could add laser targeting logic
                        self._picture = output_image
                    
                except Exception as e:
                    print(f"Error in laser detection: {e}")
            
        self.shooter.set_laser(False)

    def shot_complete(self) -> bool:
        return self._shot_done

    def get_picture(self) -> cv2.UMat:
        return self._picture
