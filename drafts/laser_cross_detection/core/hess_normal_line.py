import numpy as np
import numpy.typing as nptyping
import matplotlib.pyplot as plt

from dataclasses import dataclass

PI = np.pi
TWO_PI = np.pi * 2
PI_HALF = np.pi / 2
THREE_PI_HALF = 3 * np.pi / 2


def norm_vector(v: nptyping.NDArray) -> nptyping.NDArray:
    """Normalize a vector to length 1.

    Args:
        v (nptyping.NDArray): vector to normalize

    Returns:
        nptyping.NDArray: normalized vector
    """
    return v / np.linalg.norm(v)


def distance_line_point(
    p1: nptyping.NDArray, p2: nptyping.NDArray, p: nptyping.NDArray
) -> float:
    """Calculates the shortest distance between a line defined by p1 and p2
    and a point p

    Args:
        p1 (nptyping.NDArray): first point on line
        p2 (nptyping.NDArray): second point on line
        p (nptyping.NDArray): point to calculate distance from line

    Returns:
        float: distance betweeen line (p1, p2) and point p
    """
    p1, p2, p = np.array([p1, p2, p])  # make sure all inputs are numpy arrays
    return np.linalg.norm(np.cross(p2 - p1, p1 - p)) / np.linalg.norm(p2 - p1)


def get_intersect(a1, a2, b1, b2):
    """
    Returns the point of intersection of the lines passing through a2,a1 and
    b2,b1. Method is based on the cross product in homogenous coordinate
    space. A detailed explanation is provided in this blog post:
        https://imois.in/posts/line-intersections-with-cross-products/

    a1: [x, y] a point on the first line
    a2: [x, y] another point on the first line
    b1: [x, y] a point on the second line
    b2: [x, y] another point on the second line
    """
    s = np.vstack([a1, a2, b1, b2])  # s for stacked
    h = np.hstack((s, np.ones((4, 1))))  # h for homogeneous
    l1 = np.cross(h[0], h[1])  # get first line
    l2 = np.cross(h[2], h[3])  # get second line
    x, y, z = np.cross(l1, l2)  # point of intersection
    if z == 0:  # lines are parallel
        return (float("inf"), float("inf"))
    return (x / z, y / z)


@dataclass
class HessNormalLine:
    distance: float
    angle: float
    center: tuple[float, float] = 0, 0

    def __post_init__(self) -> None:
        self.center = np.array(self.center)
        # converte angles (including negative angles)
        # to the range (0, TWOPI]
        self.angle = (TWO_PI + self.angle) % TWO_PI

    @classmethod
    def from_degrees(cls, distance, angle, center=(0, 0)):
        return cls(distance, np.deg2rad(angle), center=center)

    @classmethod
    def from_intercept_and_slope(cls, intercept, slope, center=(0, 0)):
        """Define a line from intercept and slope. The distance is calculated
        from the triangle formed by the intercept, origin and angel (slope)."""
        angle = np.pi / 2 - np.arctan(-slope)
        distance = np.sin(angle) * intercept
        return cls(distance, angle, center=center)

    @classmethod
    def from_direction(cls, p1, direction, center=(0, 0)):
        p2 = np.add(p1, direction)
        p1_center = np.subtract(p1, center)

        # check if slope point line is above or below slope
        # import to calculate correct angle
        if np.cross(direction, p1_center) < 0:
            angle = np.arctan2(direction[1], direction[0]) - PI_HALF
        else:
            angle = np.arctan2(direction[1], direction[0]) + PI_HALF
        distance = distance_line_point(p1, p2, center)
        return cls(distance, angle, center=center)

    @classmethod
    def from_normal(cls, normal, center=(0, 0)):
        direction = -normal[1], normal[0]
        point = np.add(center, normal)
        return cls.from_direction(point, direction, center)

    @classmethod
    def from_two_points(cls, p1, p2, center=(0, 0)):
        p1, p2 = np.array(p1), np.array(p2)
        d = norm_vector(p2 - p1)
        return cls.from_direction(p1, d, center)

    @property
    def normal_point(self) -> np.ndarray:
        return self.center + self.distance * self.normal_vector

    @property
    def slope(self) -> float:
        return np.tan(self.angle + PI_HALF)

    @property
    def normal_vector(self) -> np.ndarray:
        return np.array([np.cos(self.angle), np.sin(self.angle)])

    @property
    def direction_vector(self) -> np.ndarray:
        return np.array(
            [np.cos(self.angle + PI_HALF), np.sin(self.angle + PI_HALF)]
        )

    def plot_slope(self, axis, *args, **kwds):
        return axis.axline(self.normal_point, slope=self.slope, *args, **kwds)

    def interscet_nplinalg(self, other) -> np.ndarray:
        """Calculate the intersection of two instances solving the linear
        equations defining the lines. Currently both lines need
        to share the same origin.

        Args:
            other (HessNormalLine): other instance

        Returns:
            np.ndarray: point of intersection
        """
        assert all(np.isclose(self.center, other.center))
        A = np.vstack([self.normal_vector, other.normal_vector])
        r = np.array([self.distance, other.distance])
        return np.linalg.solve(A, r) + self.center

    def intersect_crossprod(self, other) -> np.ndarray:
        """Calculate the intersection of two instances using the method of
        cross products in homogenous coordinates. Currently both lines need
        to share the same origin.

        Adapted from: https://stackoverflow.com/a/42727584
        Theorie described: https://imois.in/posts/line-intersections-with-cross-products/

        Args:
            other (HessNormalLine): other instance

        Returns:
            np.ndarray: point of intersection
        """
        assert all(np.isclose(self.center, other.center))
        a1 = self.normal_point
        a2 = self.normal_point + self.direction_vector

        b1 = other.normal_point
        b2 = other.normal_point + other.direction_vector
        return np.array(get_intersect(a1, a2, b1, b2))


if __name__ == "__main__":
    fig, ax = plt.subplots()
