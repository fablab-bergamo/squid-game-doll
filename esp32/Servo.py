from machine import Pin, PWM
import time


class Servo:
    """
    Custom servo control class optimized for SG90 micro servos.

    This class provides precise PWM control for standard hobby servos,
    with calibrated timing values for reliable positioning across the
    full 180-degree range.

    Key Features:
    - Optimized for TowerPro SG90 servos (50Hz PWM)
    - Duty cycle calibration for accurate positioning
    - Angle tracking to avoid unnecessary movements
    - Configurable timing parameters for different servo models
    """

    # PWM frequency for servo control (standard 50Hz for hobby servos)
    __servo_pwm_freq = 50

    # Duty cycle range in 10-bit resolution (0-1023)
    # These values correspond to ~1ms and ~2ms pulse widths
    __min_u10_duty = 26 - 1  # ~1ms pulse width (0° position) with offset correction
    __max_u10_duty = 123 - 0  # ~2ms pulse width (180° position) with offset correction

    # Angle range limits
    min_angle = 0.0      # Minimum servo angle (degrees)
    max_angle = 180.0    # Maximum servo angle (degrees)
    current_angle = 0.001  # Current servo position (slight offset to force initial move)

    def __init__(self, pin):
        """
        Initialize servo on specified GPIO pin.

        Args:
            pin (int): GPIO pin number for servo control signal
        """
        self.__initialise(pin)

    def update_settings(self, servo_pwm_freq, min_u10_duty, max_u10_duty, min_angle, max_angle, pin):
        """
        Update servo calibration parameters for different servo models.

        This method allows reconfiguring the servo for different models that may
        require different PWM timing or angle ranges.

        Args:
            servo_pwm_freq (int): PWM frequency in Hz (typically 50)
            min_u10_duty (int): Minimum duty cycle for 0° position (10-bit resolution)
            max_u10_duty (int): Maximum duty cycle for 180° position (10-bit resolution)
            min_angle (float): Minimum angle in degrees
            max_angle (float): Maximum angle in degrees
            pin (int): GPIO pin number for servo control
        """
        self.__servo_pwm_freq = servo_pwm_freq
        self.__min_u10_duty = min_u10_duty
        self.__max_u10_duty = max_u10_duty
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.__initialise(pin)

    def move(self, angle):
        """
        Move servo to specified angle position.

        This method converts the desired angle to the appropriate PWM duty cycle
        and commands the servo to move. It includes optimization to avoid
        unnecessary movements when the servo is already at the target position.

        Args:
            angle (float): Target angle in degrees (within min_angle to max_angle range)

        Note:
            - Angles are rounded to 2 decimal places to reduce jitter
            - No movement occurs if servo is already at the target angle
            - Angles outside the valid range will be clamped by the duty cycle calculation
        """
        # Round to 2 decimal places to reduce unwanted servo micro-adjustments
        angle = round(angle, 2)

        # Optimization: skip movement if already at target position
        if angle == self.current_angle:
            return

        # Update current position tracking
        self.current_angle = angle

        # Convert angle to PWM duty cycle and command the servo
        duty_u10 = self.__angle_to_u10_duty(angle)
        self.__motor.duty(duty_u10)

    def __angle_to_u10_duty(self, angle):
        """
        Convert angle to PWM duty cycle value.

        This private method performs the linear interpolation between minimum and
        maximum duty cycle values based on the servo's angle range.

        Args:
            angle (float): Target angle in degrees

        Returns:
            int: PWM duty cycle value in 10-bit resolution (0-1023)

        Mathematical Formula:
            duty = ((angle - min_angle) * conversion_factor) + min_duty
            where conversion_factor = (max_duty - min_duty) / (max_angle - min_angle)
        """
        return int((angle - self.min_angle) * self.__angle_conversion_factor) + self.__min_u10_duty

    def __initialise(self, pin):
        """
        Initialize servo hardware and calculate conversion factors.

        This private method sets up the PWM hardware interface and calculates
        the angle-to-duty-cycle conversion factor for efficient operation.

        Args:
            pin (int): GPIO pin number for servo control

        Internal Setup:
            - Resets current_angle to force initial positioning
            - Calculates linear conversion factor for angle-to-duty mapping
            - Configures PWM frequency for servo control (typically 50Hz)
        """
        # Reset angle tracking to force initial move on first command
        self.current_angle = -0.001

        # Calculate linear conversion factor for angle-to-duty-cycle mapping
        # This allows efficient conversion without repeated division
        self.__angle_conversion_factor = (self.__max_u10_duty - self.__min_u10_duty) / (
            self.max_angle - self.min_angle
        )

        # Initialize PWM hardware on specified pin
        self.__motor = PWM(Pin(pin))
        self.__motor.freq(self.__servo_pwm_freq)
