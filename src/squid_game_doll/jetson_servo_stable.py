"""Stable Software PWM Implementation for Jetson Servo Control

This implementation addresses common servo jitter issues:
- Uses time.perf_counter() for microsecond precision
- Implements timing compensation for GPIO delays  
- Adds thread priority control (where possible)
- Uses duty cycle caching to reduce calculations
- Implements gradual movement to reduce sudden changes
"""

import time
import threading
import os
from .jetson_gpio_manager import gpio_manager, GPIO

# Try to set thread priority (Linux only)
try:
    import ctypes
    import ctypes.util
    
    # Load libc
    libc = ctypes.CDLL(ctypes.util.find_library('c'))
    
    # Constants for thread priority
    SCHED_FIFO = 1
    SCHED_RR = 2
    
    class SchedParam(ctypes.Structure):
        _fields_ = [('sched_priority', ctypes.c_int)]
    
    def set_thread_priority(priority=50):
        """Set thread to real-time priority (requires root or CAP_SYS_NICE)"""
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


class JetsonServoStable:
    """Improved servo control with stable PWM implementation"""
    
    def __init__(self, pin, frequency=50, min_angle=0, max_angle=180):
        if GPIO is None:
            raise RuntimeError("Jetson.GPIO not available")
        
        # Validate pin is in the proven working set
        validated_pins = {7, 15, 29, 31, 32, 33}
        if pin not in validated_pins:
            raise ValueError(f"Pin {pin} not in validated pin set {validated_pins}")
            
        self.pin = pin
        self.frequency = frequency
        self.min_angle = min_angle
        self.max_angle = max_angle
        
        # PWM timing parameters (optimized for SG90)
        self.period_us = int(1_000_000 / frequency)  # Period in microseconds
        self.min_pulse_us = 500   # 0.5ms for 0 degrees
        self.max_pulse_us = 2500  # 2.5ms for 180 degrees  
        self.neutral_pulse_us = 1500  # 1.5ms for 90 degrees
        
        # State management
        self.current_angle = 90.0
        self._target_angle = 90.0
        self._cached_pulse_us = self.neutral_pulse_us
        self._pwm_running = False
        self._pwm_thread = None
        
        # Performance tracking
        self._timing_compensation_us = 0
        self._calibration_count = 0
        
        # Movement smoothing
        self.max_angle_change_per_cycle = 2.0  # Degrees per 20ms cycle
        
        # Initialize GPIO
        gpio_manager.setup_pin(pin, GPIO.OUT, initial=GPIO.LOW)
        
        # Start PWM thread
        self._pwm_running = True
        self._pwm_thread = threading.Thread(target=self._pwm_worker, daemon=True)
        self._pwm_thread.start()
        
        # Move to center position
        self.move(90.0)
    
    def _calculate_pulse_width_us(self, angle):
        """Calculate pulse width in microseconds for given angle"""
        # Clamp angle to valid range
        angle = max(self.min_angle, min(self.max_angle, angle))
        
        # Linear interpolation between min and max pulse widths
        angle_ratio = (angle - self.min_angle) / (self.max_angle - self.min_angle)
        pulse_us = self.min_pulse_us + (self.max_pulse_us - self.min_pulse_us) * angle_ratio
        
        return int(pulse_us)
    
    def _smooth_angle_transition(self, target_angle):
        """Gradually change angle to reduce servo stress and jitter"""
        angle_diff = target_angle - self.current_angle
        
        if abs(angle_diff) <= self.max_angle_change_per_cycle:
            self.current_angle = target_angle
        else:
            # Move gradually towards target
            direction = 1 if angle_diff > 0 else -1
            self.current_angle += direction * self.max_angle_change_per_cycle
            
        return self.current_angle
    
    def _pwm_worker(self):
        """High-precision PWM worker thread with timing compensation"""
        
        # Try to set high thread priority for better timing
        priority_set = set_thread_priority(80)
        
        # Calibrate timing compensation
        self._calibrate_timing_compensation()
        
        while self._pwm_running:
            try:
                # Smooth angle transition
                smooth_angle = self._smooth_angle_transition(self._target_angle)
                
                # Calculate pulse width (cache for performance)
                target_pulse_us = self._calculate_pulse_width_us(smooth_angle)
                if target_pulse_us != self._cached_pulse_us:
                    self._cached_pulse_us = target_pulse_us
                
                # High-precision timing using perf_counter
                cycle_start = time.perf_counter()
                
                # HIGH pulse with compensation
                gpio_manager.output(self.pin, GPIO.HIGH)
                pulse_end = cycle_start + (self._cached_pulse_us - self._timing_compensation_us) * 1e-6
                
                # Busy wait for precise timing (more accurate than sleep for short durations)
                while time.perf_counter() < pulse_end:
                    pass
                
                # LOW pulse
                gpio_manager.output(self.pin, GPIO.LOW)
                
                # Wait for rest of period
                period_end = cycle_start + self.period_us * 1e-6
                remaining_time = period_end - time.perf_counter()
                
                if remaining_time > 0.001:  # Use sleep for longer waits (> 1ms)
                    time.sleep(remaining_time - 0.0005)  # Sleep most of it
                    # Busy wait the last bit for precision
                    while time.perf_counter() < period_end:
                        pass
                else:
                    # Just busy wait if remaining time is short
                    while time.perf_counter() < period_end:
                        pass
                        
            except RuntimeError:
                # GPIO pin was cleaned up, exit gracefully
                break
            except Exception:
                # Other errors, exit gracefully  
                break
    
    def _calibrate_timing_compensation(self):
        """Calibrate GPIO switching delay for timing compensation"""
        if not self._pwm_running:
            return
            
        # Measure GPIO switching time
        total_delay = 0
        samples = 100
        
        for _ in range(samples):
            start = time.perf_counter()
            gpio_manager.output(self.pin, GPIO.HIGH)
            gpio_manager.output(self.pin, GPIO.LOW)
            end = time.perf_counter()
            total_delay += (end - start)
        
        # Average delay in microseconds
        self._timing_compensation_us = (total_delay / samples) * 1_000_000 / 2  # Divide by 2 for single transition
        self._calibration_count += 1
        
    def move(self, angle):
        """Set target angle for servo movement"""
        self._target_angle = max(self.min_angle, min(self.max_angle, float(angle)))
    
    def move_smooth(self, angle, speed_dps=60):
        """Move to angle with specified speed in degrees per second"""
        self.max_angle_change_per_cycle = speed_dps / self.frequency
        self.move(angle)
    
    def get_angle(self):
        """Get current servo angle"""
        return self.current_angle
    
    def is_moving(self):
        """Check if servo is still moving to target"""
        return abs(self.current_angle - self._target_angle) > 0.1
    
    def update_settings(self, min_angle=None, max_angle=None, frequency=None):
        """Update servo parameters"""
        if min_angle is not None:
            self.min_angle = min_angle
        if max_angle is not None:
            self.max_angle = max_angle
        if frequency is not None:
            self.frequency = frequency
            self.period_us = int(1_000_000 / frequency)
    
    def get_stats(self):
        """Get performance statistics"""
        return {
            'timing_compensation_us': self._timing_compensation_us,
            'calibration_count': self._calibration_count,
            'current_angle': self.current_angle,
            'target_angle': self._target_angle,
            'is_moving': self.is_moving(),
            'cached_pulse_us': self._cached_pulse_us
        }
    
    def cleanup(self):
        """Clean shutdown of PWM thread and GPIO"""
        # Stop PWM thread first, then cleanup GPIO
        self._pwm_running = False
        if self._pwm_thread and self._pwm_thread.is_alive():
            self._pwm_thread.join(timeout=1.0)  # Longer timeout for stable shutdown
        
        # Set servo to neutral position before cleanup
        try:
            gpio_manager.output(self.pin, GPIO.LOW)
        except:
            pass
            
        # Only cleanup GPIO after thread has stopped
        if hasattr(self, 'pin'):
            gpio_manager.cleanup_pin(self.pin)
    
    def __del__(self):
        try:
            self.cleanup()
        except:
            pass