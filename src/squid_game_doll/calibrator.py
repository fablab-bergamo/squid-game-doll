from .laser_finder import LaserFinder
from .laser_shooter import LaserShooter
from Camera import Camera
import cv2
from time import sleep


class Calibrator:
    def __init__(self, camera: Camera, finder: LaserFinder, tracker: LaserShooter):
        self.finder = finder
        self.tracker = tracker
        self.cam = camera
        if not self.cam.isOpened():
            raise Exception("Invalid camera state")

    def calibrate(self) -> bool:
        limits = self.tracker.get_limits()

        while limits is None:
            limits = self.tracker.get_limits()
            sleep(0.5)

        upper_left = (limits[0][0], limits[1][1])
        upper_right = (limits[0][1], limits[1][1])
        down_left = (limits[0][0], limits[1][0])
        down_right = (limits[0][1], limits[1][0])

        positions = [upper_left, upper_right, down_right, down_left]
        pixels = {}

        cv2.namedWindow("Calibration", cv2.WINDOW_NORMAL)

        while len(pixels) < len(positions):
            for pos in positions:
                if not self.tracker.send_angles(pos):
                    return False

                # Skip a few frames
                for _ in range(5):
                    frame = self.cam.read_resize()
                    sleep(0.1)

                # Now try to find the laser
                for _ in range(3):
                    frame = self.cam.read_resize()
                    if frame is None:
                        return False
                    cv2.imshow("Calibration", frame)
                    cv2.waitKey(1)
                    _, img = self.finder.find_laser(frame, [])
                    if self.finder.laser_found():
                        pixels[pos] = self.finder.get_laser_coord()
                        break

        self.calibration_data = pixels
        cv2.destroyWindow("Calibration")
        print(f"Calibration={self.calibration_data}")
        self.compute()
        sleep(1)
        return True

    def compute(self) -> float:
        prev_pos = None
        for pos in self.calibration_data.keys():
            if prev_pos is not None:
                delta_v = prev_pos[0] - pos[0]
                delta_h = prev_pos[1] - pos[1]
                if delta_v != 0:
                    delta_px_v = self.calibration_data[prev_pos][1] - self.calibration_data[pos][1]
                    if delta_px_v != 0:
                        self.px_per_angle_v = round(delta_px_v / delta_v, 2)
                if delta_h != 0:
                    delta_px_h = self.calibration_data[prev_pos][0] - self.calibration_data[pos][0]
                    if delta_px_h != 0:
                        self.px_per_angle_h = round(delta_px_h / delta_h, 2)
            else:
                prev_pos = pos
        print(f"Px/° H={self.px_per_angle_h}")
        print(f"Px/° V={self.px_per_angle_v}")
