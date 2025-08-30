"""Unified Jetson PWM Controller - Handles both servo and LED PWM with minimal code"""

import time
import threading
import math
from .jetson_gpio_manager import gpio_manager, GPIO

try:
    import ctypes
    import ctypes.util
    libc = ctypes.CDLL(ctypes.util.find_library('c'))
    SCHED_RR = 2
    class SchedParam(ctypes.Structure):
        _fields_ = [('sched_priority', ctypes.c_int)]
    def set_thread_priority(priority=50):
        try:
            param = SchedParam()
            param.sched_priority = priority
            result = libc.sched_setscheduler(0, SCHED_RR, ctypes.byref(param))
            return result == 0
        except:
            return False
except ImportError:
    def set_thread_priority(priority=50):
        return False


class JetsonPWM:
    """Unified PWM controller for servos and LEDs"""
    
    def __init__(self, pin, pwm_type="servo", frequency=50, min_val=0, max_val=180):
        if GPIO is None:
            raise RuntimeError("Jetson.GPIO not available")
        
        validated_pins = {7, 15, 29, 31, 32, 33}
        if pin not in validated_pins:
            raise ValueError(f"Pin {pin} not in validated pin set {validated_pins}")
            
        self.pin = pin
        self.pwm_type = pwm_type  # "servo" or "led"
        self.frequency = frequency
        self.min_val = min_val
        self.max_val = max_val
        
        if pwm_type == "servo":
            self.period_us = int(1_000_000 / frequency)
            self.min_pulse_us = 500   # 0.5ms
            self.max_pulse_us = 2500  # 2.5ms
            self._current_val = 90.0  # Center position
            self._target_val = 90.0
            self.smooth_step = 2.0    # Degrees per cycle
        else:  # LED
            self.period_us = int(1_000_000 / frequency)
            self._current_val = 0.0   # Off
            self._target_val = 0.0
            self.smooth_step = 5.0    # Brightness per cycle
            self.gamma = 2.2
        
        self._pwm_running = False
        self._pwm_thread = None
        self._cached_pulse_us = 0
        
        gpio_manager.setup_pin(pin, GPIO.OUT, initial=GPIO.LOW)
        self._pwm_running = True
        self._pwm_thread = threading.Thread(target=self._pwm_worker, daemon=True)
        self._pwm_thread.start()
    
    def _calc_servo_pulse_us(self, angle):
        angle = max(self.min_val, min(self.max_val, angle))
        ratio = (angle - self.min_val) / (self.max_val - self.min_val)
        return int(self.min_pulse_us + (self.max_pulse_us - self.min_pulse_us) * ratio)
    
    def _calc_led_duty_us(self, brightness):
        if brightness <= 0:
            return 0
        brightness = max(0, min(100, brightness))
        # Apply gamma correction
        corrected = (brightness / 100.0) ** self.gamma * 100.0
        return int((corrected / 100.0) * self.period_us)
    
    def _smooth_transition(self):
        if abs(self._target_val - self._current_val) <= self.smooth_step:
            self._current_val = self._target_val
        else:
            direction = 1 if self._target_val > self._current_val else -1
            self._current_val += direction * self.smooth_step
    
    def _pwm_worker(self):
        set_thread_priority(80)
        
        while self._pwm_running:
            try:
                self._smooth_transition()
                
                if self.pwm_type == "servo":
                    pulse_us = self._calc_servo_pulse_us(self._current_val)
                else:
                    pulse_us = self._calc_led_duty_us(self._current_val)
                
                if pulse_us != self._cached_pulse_us:
                    self._cached_pulse_us = pulse_us
                
                cycle_start = time.perf_counter()
                
                if self._cached_pulse_us > 0:
                    gpio_manager.output(self.pin, GPIO.HIGH)
                    pulse_end = cycle_start + self._cached_pulse_us * 1e-6
                    while time.perf_counter() < pulse_end:
                        pass
                    gpio_manager.output(self.pin, GPIO.LOW)
                
                period_end = cycle_start + self.period_us * 1e-6
                remaining = period_end - time.perf_counter()
                if remaining > 0.001:
                    time.sleep(remaining - 0.0005)
                while time.perf_counter() < period_end:
                    pass
                        
            except (RuntimeError, Exception):
                break
    
    def set_value(self, value):
        """Set servo angle (0-180) or LED brightness (0-100)"""
        self._target_val = max(self.min_val, min(self.max_val, float(value)))
    
    def get_value(self):
        return self._current_val
    
    def is_moving(self):
        return abs(self._current_val - self._target_val) > 0.1
    
    def cleanup(self):
        self._pwm_running = False
        if self._pwm_thread and self._pwm_thread.is_alive():
            self._pwm_thread.join(timeout=1.0)
        try:
            gpio_manager.output(self.pin, GPIO.LOW)
        except:
            pass
        if hasattr(self, 'pin'):
            gpio_manager.cleanup_pin(self.pin)
    
    def __del__(self):
        try:
            self.cleanup()
        except:
            pass


# Compatibility classes
class JetsonServoStable(JetsonPWM):
    def __init__(self, pin, frequency=50, min_angle=0, max_angle=180):
        super().__init__(pin, "servo", frequency, min_angle, max_angle)
        self.current_angle = self._current_val
    
    def move(self, angle):
        self.set_value(angle)
        self.current_angle = self._target_val
    
    def get_angle(self):
        return self.get_value()
    
    def update_settings(self, min_angle, max_angle):
        self.min_val = min_angle
        self.max_val = max_angle


class JetsonEyesStable(JetsonPWM):
    def __init__(self, pin, frequency=1000):
        super().__init__(pin, "led", frequency, 0, 100)
    
    def set_brightness(self, brightness):
        self.set_value(brightness)
    
    def set_brightness_smooth(self, brightness, transition_speed=5.0):
        self.smooth_step = transition_speed
        self.set_brightness(brightness)
    
    def get_brightness(self):
        return self.get_value()
    
    def is_changing(self):
        return self.is_moving()