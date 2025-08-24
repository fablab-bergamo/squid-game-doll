from typing import Callable
import cv2

# from drafts.gradient_search import test_gradient
# from drafts.motion_pattern import motion_pattern_analysis
from .display import add_exclusion_rectangles
from .img_processing import brightness

DEBUG_LASER_FIND = False


# source tbc https://stackoverflow.com/questions/9860667/writing-robust-color-and-size-invariant-circle-detection-with-opencv-based-on
# source tbc https://www.pyimagesearch.com/2014/07/21/detecting-circles-images-using-opencv-hough-circles/
# source tbc https://www.pyimagesearch.com/2016/02/15/determining-object-color-with-opencv/
class LaserFinder:
    def __init__(self):
        """
        Initializes the LaserFinder object.
        """
        self.prev_strategy = None
        self.prev_threshold = None
        self.laser_coord = None
        self.prev_img = None
        self.prev_candidates = []

    def laser_found(self) -> bool:
        return self.laser_coord is not None

    def get_laser_coord(self) -> tuple[int, int]:
        return self.laser_coord

    def get_winning_strategy(self) -> str:
        if self.laser_found():
            return f"{self.prev_strategy}(THR={self.prev_threshold})"
        return ""

    def find_laser(self, img: cv2.UMat, rects: list) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given image using different strategies.

        Parameters:
        img (cv2.UMat): The input image.

        Returns:
        tuple: The coordinates of the laser, the output image, the strategy used, and the threshold value.
        """
        add_exclusion_rectangles(img, rects, (0, 0, 0))
        strategies = [
            self.find_laser_by_red_color,
            self.find_laser_by_grayscale,
        ]  # , self.find_laser_by_green_color, self.find_laser_by_gray_centroids]

        for strategy in strategies:
            if DEBUG_LASER_FIND:
                print(f"Trying strategy {strategy.__name__}")

            (coord, output) = strategy(img.copy())
            if coord is not None:
                print(f"Found laser at {coord}")
                cv2.putText(
                    output,
                    text=strategy.__name__,
                    org=(10, 40),
                    fontFace=cv2.FONT_HERSHEY_COMPLEX,
                    fontScale=0.5,
                    color=(0, 255, 0),
                )
                cv2.putText(
                    output,
                    text=f"Brightness={int(brightness(img))}",
                    org=(10, 60),
                    fontFace=cv2.FONT_HERSHEY_COMPLEX,
                    fontScale=0.5,
                    color=(0, 255, 0),
                )
                self.prev_strategy = strategy.__name__
                self.laser_coord = coord
                return (coord, output)

        self.laser_coord = None

        if DEBUG_LASER_FIND:
            print("No laser found")

        return (None, None)

    def find_laser_by_threshold(
        self, channel: cv2.UMat, searchfunction: Callable[[cv2.UMat], list]
    ) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given channel using a thresholding strategy.

        Parameters:
        channel (cv2.UMat): The input channel.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        MAX_TRIES = 7
        MIN_THRESHOLD = 100
        MAX_THRESHOLD = 255
        threshold = (MIN_THRESHOLD + MAX_THRESHOLD) // 2

        if (
            self.prev_threshold is not None
            and self.prev_threshold > MIN_THRESHOLD
            and self.prev_threshold < MAX_THRESHOLD
        ):
            threshold = self.prev_threshold

        tries = 0
        while tries < MAX_TRIES:
            if DEBUG_LASER_FIND:
                print(f"Try: {tries}/{MAX_TRIES}")

            _, diff_thr = cv2.threshold(channel, threshold, 255, cv2.THRESH_TOZERO)
            # cv2.imshow("Threshold", cv2.cvtColor(diff_thr, cv2.COLOR_GRAY2BGR))

            masked_channel = cv2.dilate(diff_thr, None, iterations=4)
            # cv2.imshow("Dilate", cv2.cvtColor(masked_channel, cv2.COLOR_GRAY2BGR))

            circles = searchfunction(masked_channel)

            circles_cpt = len(circles)

            if circles_cpt == 0:
                step = (threshold - MIN_THRESHOLD) // 2
                if step == 0:
                    step = 1
                threshold -= step

                if DEBUG_LASER_FIND:
                    print(f"Found no circles, decreasing threshold to {threshold}")

                if threshold < MIN_THRESHOLD:
                    self.laser_coord = None
                    self.prev_threshold = None
                    return (None, None)
                tries += 1
                continue

            if circles_cpt > 1 or (self.laser_coord is not None and circles_cpt > 5):
                step = (MAX_THRESHOLD - threshold) // 2
                if step == 0:
                    step = 1
                threshold += step

                if DEBUG_LASER_FIND:
                    print(f"Found {circles_cpt} circles, increasing threshold to {threshold}")

                if threshold > MAX_THRESHOLD:
                    self.laser_coord = None
                    self.prev_threshold = None
                    return (None, None)
                tries += 1
                continue

            # draw circles found
            output = cv2.cvtColor(masked_channel, cv2.COLOR_GRAY2BGR)
            background = cv2.cvtColor(channel, cv2.COLOR_GRAY2BGR)

            if self.laser_coord and circles_cpt > 1:
                if DEBUG_LASER_FIND:
                    print(f"Selected closest circle to previous position")
                circles.sort(key=lambda c: (c[0] - self.laser_coord[0]) ** 2 + (c[1] - self.laser_coord[1]) ** 2)

            center = (int(circles[0][0]), int(circles[0][1]))
            output = cv2.addWeighted(background, 0.2, output, 0.5, 0)
            cv2.putText(
                output,
                text="THR=" + str(threshold),
                org=(10, 20),
                fontFace=cv2.FONT_HERSHEY_COMPLEX,
                fontScale=0.5,
                color=(0, 255, 0),
            )
            self.prev_threshold = threshold
            self.laser_coord = center
            return (center, output)

        self.laser_coord = None
        return (None, None)

    def search_by_hough_circles(self, channel: cv2.UMat) -> list:

        if DEBUG_LASER_FIND:
            cv2.imshow("HoughCircles", channel)
            cv2.waitKey(1)

        circles = cv2.HoughCircles(
            image=channel,
            method=cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=2,
            minRadius=4,
            maxRadius=10,
        )

        if circles is None:
            if DEBUG_LASER_FIND:
                print("no circle found")

            return []

        return circles[0, :]

    """
    def search_by_modified_gradiant(self, channel: cv2.UMat) -> list:

        circles = test_gradient(channel)

        if circles is None or len(circles) == 0:
            return []

        self.prev_img = channel
        self.prev_candidates = circles
        return [x["position"] for x in circles]

    def search_by_motion_analysis(self, channel: cv2.UMat) -> list:

        candidates = test_gradient(channel)

        _, best_candidate = motion_pattern_analysis(
            candidates,
            self.prev_candidates,
            channel,
            self.prev_img,
            C1=2.0,
            C2=0.2,
            assoc_thresh=10.0,
        )

        self.prev_img = channel
        self.prev_candidates = candidates

        if best_candidate is None:
            return []

        return best_candidate["position"]
    """

    def search_by_contours(self, channel: cv2.UMat) -> list:
        max_radius = 20
        # Find contours
        contours, _ = cv2.findContours(channel, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Convert grayscale image to BGR for visualization
        result = cv2.cvtColor(channel, cv2.COLOR_GRAY2BGR)

        detected_centroids = []

        for contour in contours:
            # Fit a minimum enclosing circle to estimate the size
            (x, y), radius = cv2.minEnclosingCircle(contour)
            radius = int(radius)

            # Filter based on the maximum allowed radius
            if radius <= max_radius:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    detected_centroids.append((cx, cy))

                    # Draw contour and centroid for visualization
                    cv2.drawContours(result, [contour], -1, (0, 255, 0), 2)
                    cv2.circle(result, (cx, cy), 5, (0, 0, 255), -1)
                    cv2.putText(
                        result,
                        f"({cx},{cy})",
                        (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 0, 0),
                        1,
                    )

        cv2.imshow("Contours", result)
        return detected_centroids

    def find_laser_by_threshold_2(self, channel: cv2.UMat) -> tuple[tuple, cv2.UMat]:
        """
        Finds the laser in the given channel using a thresholding strategy.

        Parameters:
        channel (cv2.UMat): The input channel.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        MAX_TRIES = 100
        MIN_THRESHOLD = 50
        MAX_THRESHOLD = 255
        threshold = (MIN_THRESHOLD + MAX_THRESHOLD) // 2
        step = (MIN_THRESHOLD + MAX_THRESHOLD) // 4

        if (
            self.prev_threshold is not None
            and self.prev_threshold > MIN_THRESHOLD
            and self.prev_threshold < MAX_THRESHOLD
        ):
            threshold = self.prev_threshold

        tries = 0
        while tries < MAX_TRIES:
            _, diff_thr = cv2.threshold(channel, threshold, 255, cv2.THRESH_TOZERO)
            # cv2.imshow("Threshold", cv2.cvtColor(diff_thr, cv2.COLOR_GRAY2BGR))
            img_conv = cv2.cvtColor(diff_thr, cv2.COLOR_BGR2GRAY)

            pixels = cv2.countNonZero(img_conv)

            if pixels == 0:
                step = 1
                if step == 0:
                    step = 1
                threshold -= step
                # print(f"Found no pixels, decreasing threshold to {threshold}")
                if threshold < MIN_THRESHOLD:
                    self.laser_coord = None
                    self.prev_threshold = None
                    return (None, None)
                tries += 1
                continue

            if pixels > 100:
                step = 1
                if step == 0:
                    step = 1
                threshold += step
                # print(f"Found {pixels} pixels, increasing threshold to {threshold}")
                if threshold > MAX_THRESHOLD:
                    self.laser_coord = None
                    self.prev_threshold = None
                    return (None, None)
                tries += 1
                continue

            print(f"Found <100 highest pixels, threshold={threshold}")

            # find countours
            circles = cv2.HoughCircles(
                img_conv,
                cv2.HOUGH_GRADIENT,
                1,
                minDist=50,
                param1=50,
                param2=2,
                minRadius=3,
                maxRadius=10,
            )

            if circles is not None:
                for circle in circles[0, :]:
                    cv2.circle(
                        img_conv,
                        (int(circle[0]), int(circle[1])),
                        int(circle[2]),
                        (255, 0, 0),
                        1,
                    )

            cv2.imshow("Contours", img_conv)
            return ((1, 1), img_conv)

        self.laser_coord = (1, 1)
        return ((1, 1), None)

    def find_laser_by_grayscale(self, img: cv2.UMat) -> tuple[tuple, cv2.UMat]:
        """
        Finds the laser in the given image using a grayscale strategy.

        Parameters:
        img (cv2.UMat): The input image.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        normalized_gray_image = cv2.normalize(gray_image, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        return self.find_laser_by_threshold(normalized_gray_image, searchfunction=self.search_by_hough_circles)

    def find_laser_by_red_color(self, img: cv2.UMat) -> tuple[tuple, cv2.UMat]:
        """
        Finds the laser in the given image using the red color channel.

        Parameters:
        img (cv2.UMat): The input image.
        hint (int): The threshold hint to use for the strategy.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        (_, _, R) = cv2.split(img)
        return self.find_laser_by_threshold(R, searchfunction=self.search_by_hough_circles)

    def find_laser_by_green_color(self, img: cv2.UMat) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given image using the green color channel.

        Parameters:
        img (cv2.UMat): The input image.
        hint (int): The threshold hint to use for the strategy.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        (_, G, _) = cv2.split(img)
        return self.find_laser_by_threshold(G, searchfunction=self.search_by_hough_circles)

    def find_laser_by_red_color_motion(self, img: cv2.UMat) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given image using the red color channel.

        Parameters:
        img (cv2.UMat): The input image.
        hint (int): The threshold hint to use for the strategy.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        (_, _, R) = cv2.split(img)
        return self.find_laser_by_threshold(R, searchfunction=self.search_by_motion_analysis)

    def find_laser_by_gray_centroids(self, img: cv2.UMat) -> (tuple, cv2.UMat):
        """
        Finds the laser in the given image using the red color channel.

        Parameters:
        img (cv2.UMat): The input image.
        hint (int): The threshold hint to use for the strategy.

        Returns:
        tuple: The coordinates of the laser, the output image, and the threshold value.
        """
        gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        normalized_gray_image = cv2.normalize(gray_image, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
        return self.find_laser_by_threshold(normalized_gray_image, searchfunction=self.search_by_contours)
