import numpy as np
import socket
from typing import Tuple
from numpy.linalg import norm
from time import time, sleep
from simple_pid import PID
import ast
from loguru import logger

# Configuration constants
DEFAULT_ESP32_PORT = 15555
DEFAULT_DEADBAND_PX = 10
DEFAULT_MAX_FREQUENCY_HZ = 10
DEFAULT_PX_PER_DEGREE_H = 50.0
DEFAULT_PX_PER_DEGREE_V = 15.0
DEFAULT_PID_KP = 0.1
PID_KI_FACTOR = 0.6
PID_KD_FACTOR = 0.3
MIN_STEP_SIZE = 0.8
MAX_STEP_SIZE = 20
RATE_LIMIT_MAX_CHANGE = 100
SOCKET_RECV_BUFFER_SIZE = 128
SOCKET_RECV_BUFFER_SIZE_SMALL = 64
MAX_CONNECTION_ATTEMPTS = 3


class LaserShooter:

    def __init__(self, ipaddress: str, deadband_px: int = DEFAULT_DEADBAND_PX, max_frequency_hz: int = DEFAULT_MAX_FREQUENCY_HZ, enable_laser: bool = True):
        """
        Initializes the LaserShooter object with the given IP address, deadband, and maximum frequency.

        Parameters:
        ipaddress (str): The IP address of the ESP32.
        deadband_px (int): The deadband in pixels.
        max_frequency_hz (int): The maximum frequency in Hz.
        """
        self._is_online = False
        self.ip_address = ipaddress
        self.port = DEFAULT_ESP32_PORT
        self.aliensocket: socket = None
        self.last_sent: int = 0
        self.deadband: int = deadband_px
        self.min_period_S: float = 1.0 / max_frequency_hz
        self.limits: Tuple[float, float] = self.get_limits()
        self.pid_ok: bool = self.init_PID()
        self.coeffs: Tuple[float, float] = (DEFAULT_PX_PER_DEGREE_H, DEFAULT_PX_PER_DEGREE_V)
        self._enable_laser = enable_laser

    def is_laser_enabled(self) -> bool:
        """Check if laser functionality is enabled.
        
        Returns:
            bool: True if laser is enabled, False otherwise
        """
        return self._enable_laser

    def set_coeffs(self, px_per_degree: Tuple[float, float]):
        """Set the pixel per degree conversion coefficients.
        
        Args:
            px_per_degree: Tuple of (horizontal_coeff, vertical_coeff) for pixel to degree conversion
        """
        if px_per_degree is not None:
            self.coeffs = px_per_degree

    def init_PID(self) -> bool:
        """
        Initializes the PID controllers for horizontal and vertical movements.
        """
        if self.limits is None:
            self.limits = self.get_limits()

        if self.limits is not None:
            zero = self.__getzeropos()
            k = DEFAULT_PID_KP
            self.pid_v = PID(
                k,
                k * PID_KI_FACTOR,
                k * PID_KD_FACTOR,
                setpoint=0,
                output_limits=(self.limits[1][0], self.limits[1][1]),
                starting_output=zero[1],
            )
            self.pid_h = PID(
                k,
                k * PID_KI_FACTOR,
                k * PID_KD_FACTOR,
                setpoint=0,
                output_limits=(self.limits[0][0], self.limits[0][1]),
                starting_output=zero[0],
            )
            self.pid_h.sample_time = self.min_period_S
            self.pid_v.sample_time = self.min_period_S
            self.send_angles(zero)
            self.prev_output_h = zero[0]
            self.prev_output_v = zero[1]
            return True

            logger.error("PID initialization failure")
        return False

    def set_laser(self, on_or_off: bool) -> bool:
        if not self.isOnline():
            return False
        if on_or_off:
            return self._send_msg("ON")
        return self._send_msg("OFF")

    def rotate_head(self, green_light: bool) -> bool:
        if green_light:
            return self._send_msg("h1")
        return self._send_msg("h0")

    def set_eyes(self, eyes_on: bool) -> bool:
        if eyes_on:
            return self._send_msg("e1")
        return self._send_msg("e0")

    def isOnline(self) -> bool:
        """
        Checks if the LaserShooter is online.

        Returns:
        bool: True if online, False otherwise.
        """
        return self._is_online

    def track_target(self, laser: tuple, target: tuple) -> float:
        """
        Tracks the target position relative to the laser position and provides feedback.

        Parameters:
        laser (tuple): The (x, y) coordinates of the laser position.
        target (tuple): The (x, y) coordinates of the target position.

        Returns:
        float: The positioning error in absolute distance.
        """
        # compute the positionning error in abs distance
        if target is None or laser is None:
            return 0

        error = norm(np.array(laser) - np.array(target))

        vertical_error = laser[1] - target[1]
        horizontal_error = laser[0] - target[0]

        up = False
        down = False
        left = False
        right = False

        if vertical_error < -1 * self.deadband:
            down = True
        elif vertical_error > self.deadband:
            up = True

        if horizontal_error < -1 * self.deadband:
            right = True
        elif horizontal_error > self.deadband:
            left = True

        step_v = min(max(MIN_STEP_SIZE, abs(vertical_error / self.coeffs[1])), MAX_STEP_SIZE)
        step_h = min(max(MIN_STEP_SIZE, abs(horizontal_error / self.coeffs[0])), MAX_STEP_SIZE)

        logger.debug(f"Laser {laser} Target {target}")
        logger.debug(f"Up:{up}, Down:{down}, Left:{left}, Right:{right}")
        logger.debug(f"Step V {step_v}, step H {step_h}")

        self.send_instructions(up, down, left, right, step_v, step_h)
        # Send the updated angles to ESP32
        return error

    def track_target_PID(self, laser: tuple, target: tuple) -> float:
        """
        Tracks the target position relative to the laser position using PID control and provides feedback.

        Parameters:
        laser (tuple): The (x, y) coordinates of the laser position.
        target (tuple): The (x, y) coordinates of the target position.

        Returns:
        float: The positioning error in absolute distance.
        """
        RATE_OF_CHANGE = RATE_LIMIT_MAX_CHANGE

        if not self.pid_ok:
            self.pid_ok = self.init_PID()
            if not self.pid_ok:
                logger.warning("PID not initialized")
                return 0.0

        if target is None or laser is None:
            return 0

        error = norm(np.array(laser) - np.array(target))

        vertical_error = -1 * (laser[1] - target[1])
        horizontal_error = -1 * (laser[0] - target[0])

        output_h = self.pid_h(horizontal_error)
        output_v = self.pid_v(vertical_error)

        if abs(output_h - self.prev_output_h) > RATE_OF_CHANGE:
            logger.debug(f"Rate limiting H from {output_h} to {RATE_OF_CHANGE}")
            if output_h > self.prev_output_h:
                output_h = self.prev_output_h + RATE_OF_CHANGE
            else:
                output_h = self.prev_output_h - RATE_OF_CHANGE

        if abs(output_v - self.prev_output_v) > RATE_OF_CHANGE:
            logger.debug(f"Rate limiting V from {output_v} to {RATE_OF_CHANGE}")
            if output_v > self.prev_output_v:
                output_v = self.prev_output_v + RATE_OF_CHANGE
            else:
                output_v = self.prev_output_v - RATE_OF_CHANGE

        if output_h != self.prev_output_h or output_v != self.prev_output_v:
            if self.send_angles((output_h, output_v)):
                self.prev_output_h = output_h
                self.prev_output_v = output_v

        return error

    def __getzeropos(self) -> tuple:
        if self.limits is not None:
            start_v = (self.limits[1][1] - self.limits[1][0]) / 2 + self.limits[1][0]
            start_h = (self.limits[0][1] - self.limits[0][0]) / 2 + self.limits[0][0]
            return (start_h, start_v)
        return None

    def reset_pos(self) -> bool:
        """
        Resets the position of the servos to the center of their limits.

        Returns:
        bool: True if the position is successfully reset, False otherwise.
        """
        if self.limits is not None:
            return self.send_angles(self.__getzeropos())
        return False

    def get_angles(self) -> Tuple:
        """Get current servo angles from ESP32.
        
        Returns:
            Tuple of (horizontal_angle, vertical_angle) or None if communication fails
        """
        """
        Gets the current angles of the servos from the ESP32.

        Returns:
        tuple: The current angles of the servos, or None if the ESP32 is not reachable.
        """
        data = bytes("angles" + "\n", "utf-8")  # ### CHANGED: Append newline as delimiter

        if not self.__checksocket():
            return None

        try:
            logger.debug(f"Sending to ESP32: {data}")
            self.aliensocket.sendall(data)
            response = self.aliensocket.recv(128)
            logger.debug(f"ESP32 response: {response}")
            self._is_online = True
            return ast.literal_eval(response.decode("utf-8"))
        except (socket.error, ConnectionError, OSError) as e:
            logger.error(f"get_angles: network failure to contact ESP32: {e}")
        except (ValueError, SyntaxError) as e:
            logger.error(f"get_angles: data parsing error from ESP32: {e}")
        except Exception as e:
            logger.error(f"get_angles: unexpected error contacting ESP32: {e}")
            try:
                self.aliensocket.close()
            except:
                pass
            self.aliensocket = None
            self._is_online = False
            return None

    def get_limits(self) -> Tuple:
        """Get servo angle limits from ESP32.
        
        Returns:
            Tuple of ((h_min, h_max), (v_min, v_max)) or None if communication fails
        """
        """
        Gets the servo limits from the ESP32.

        Returns:
        tuple: The servo limits, or None if the ESP32 is not reachable.
        """
        data = bytes("limits" + "\n", "utf-8")  # ### CHANGED: Append newline as delimiter
        if not self.__checksocket():
            return None
        try:
            logger.debug(f"Sending to ESP32: {data}")
            self.aliensocket.sendall(data)
            response = self.aliensocket.recv(SOCKET_RECV_BUFFER_SIZE_SMALL)
            logger.debug(f"ESP32 response: {response}")
            self._is_online = True
            retval = ast.literal_eval(response.decode("utf-8"))
            logger.debug(f"get_limits={retval}")
            return retval
        except (socket.error, ConnectionError, OSError) as e:
            logger.error(f"get_limits: network failure to contact ESP32: {e}")
        except (ValueError, SyntaxError) as e:
            logger.error(f"get_limits: data parsing error from ESP32: {e}")
        except Exception as e:
            logger.error(f"get_limits: unexpected error contacting ESP32: {e}")
            try:
                self.aliensocket.close()
            except:
                pass
            self.aliensocket = None
            self._is_online = False
            return None

    def __checksocket(self) -> bool:
        # ### CHANGED: Implement auto-reconnect with retry logic
        if self.aliensocket is None:
            attempt = 0
            while attempt < 5:
                try:
                    logger.debug(f"__checksocket: connecting to {self.ip_address}:{self.port} (attempt {attempt+1})")
                    self.aliensocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.aliensocket.settimeout(0.5)  # ### CHANGED: Slightly longer timeout for reconnection
                    self.aliensocket.connect((self.ip_address, self.port))
                    self._is_online = True
                    return True
                except (socket.error, ConnectionError, OSError) as e:
                    logger.debug(f"__checksocket: connection attempt {attempt+1} failed: {e}")
                except Exception as e:
                    logger.debug(f"__checksocket: unexpected error on attempt {attempt+1}: {e}")
                    try:
                        self.aliensocket.close()
                    except:
                        pass
                    self.aliensocket = None
                    self._is_online = False
                    attempt += 1
                    sleep(1)  # ### CHANGED: Wait a second before retrying
            return False
        return True

    def _send_msg(self, message: str) -> bool:
        logger.debug(f"send_msg: message={message}")

        if not self.__checksocket():
            return False

        data = bytes(str(message) + "\n", "utf-8")  # ### CHANGED: Append newline as delimiter
        try:
            logger.debug(f"Sending to ESP32: {data}")
            self.aliensocket.sendall(data)
            self.aliensocket.recv(SOCKET_RECV_BUFFER_SIZE)
        except (socket.error, ConnectionError, OSError) as e:
            logger.error(f"_send_msg: network failure to contact ESP32: {e}")
        except Exception as e:
            logger.error(f"_send_msg: unexpected error contacting ESP32: {e}")
            self.aliensocket.close()
            self.aliensocket = None
            self._is_online = False
            return False

        self._is_online = True
        return True

    def send_angles(self, angles: tuple) -> bool:
        """
        Sends new angles (H,V) to ESP32.

        Parameters:
        angles (tuple): The (horizontal_angle, vertical_angle) to send.

        Returns:
        bool: True if the angles are successfully sent, False otherwise.
        """
        logger.debug(f"send_angles: target (H,V)=({round(angles[0],2)}, {round(angles[1],2)})")

        if not self.__checksocket():
            return False

        # Round angles to 2 decimals, servos will not be able to do better than 0.1° anyways
        target = (round(angles[0], 2), round(angles[1], 2))
        data = bytes(str(target) + "\n", "utf-8")  # ### CHANGED: Added newline delimiter
        try:
            logger.debug(f"Sending to ESP32: {data}")
            self.aliensocket.sendall(data)
            self.aliensocket.recv(SOCKET_RECV_BUFFER_SIZE)
        except (socket.error, ConnectionError, OSError) as e:
            logger.error(f"send_angles: network failure to contact ESP32: {e}")
        except Exception as e:
            logger.error(f"send_angles: unexpected error contacting ESP32: {e}")
            self.aliensocket.close()
            self.aliensocket = None
            self._is_online = False
            return False

        self._is_online = True
        return True

    def send_instructions(
        self,
        up: bool,
        down: bool,
        left: bool,
        right: bool,
        step_v: float,
        step_h: float,
    ) -> bool:
        """
        Sends movement instructions to the ESP32 based on the direction flags and step sizes.

        Parameters:
        up (bool): Flag indicating whether to move up.
        down (bool): Flag indicating whether to move down.
        left (bool): Flag indicating whether to move left.
        right (bool): Flag indicating whether to move right.
        step_v (float): The vertical step size.
        step_h (float): The horizontal step size.

        Returns:
        bool: True if the instructions are successfully sent, False otherwise.
        """
        if time() - self.last_sent > self.min_period_S:
            self.last_sent = time()
        else:
            return True

        self.current_pos = self.get_angles()

        if self.current_pos is None:
            logger.error("Failure to get current angles!")
            return False

        target = self.current_pos

        if up:
            target = (self.current_pos[0], self.current_pos[1] + step_v)
        if down:
            target = (self.current_pos[0], self.current_pos[1] - step_v)
        if left:
            target = (self.current_pos[0] + step_h, self.current_pos[1])
        if right:
            target = (self.current_pos[0] - step_h, self.current_pos[1])

        if self.limits is None:
            self.limits = self.get_limits()

        # Enforce limits
        if target[0] < self.limits[0][0]:
            target = (self.limits[0][0], target[1])
        if target[0] > self.limits[0][1]:
            target = (self.limits[0][1], target[1])

        if target[1] < self.limits[1][0]:
            target = (target[0], self.limits[1][0])
        if target[1] > self.limits[1][1]:
            target = (target[0], self.limits[1][1])

        result = self.send_angles(target)
        return result
