import cv2
from threading import Thread
from .laser_finder import LaserFinder
from .laser_shooter import LaserShooter


class LaserTracker:
    def __init__(self, shooter: LaserShooter):
        self.shooter: LaserShooter = shooter
        self.thread: Thread = Thread(target=self.track_and_shoot)
        self.target: tuple[int, int] = (0, 0)
        self._shot_done = False
        self.shall_run = False
        self.last_frame: cv2.UMat = None
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

    def update_frame(self, webcam: cv2.UMat) -> None:
        self.last_frame = webcam.copy()

    def stop(self):
        self.shooter.set_laser(False)
        if self.thread.is_alive():
            self.shall_run = False
            self.thread.join()
            print("stop: thread joined")

    def track_and_shoot(self) -> None:
        print("track_and_shoot: thread started")
        finder = LaserFinder()
        while self.shall_run:
            self.shooter.set_laser(True)
            pass
        self.shooter.set_laser(False)

    def shot_complete(self) -> bool:
        return self._shot_done

    def get_picture(self) -> cv2.UMat:
        return self._picture
