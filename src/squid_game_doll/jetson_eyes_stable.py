"""Stable LED PWM Implementation for Jetson Eyes Control

Improved PWM for LED brightness control with:
- High-precision timing using perf_counter()
- Optimized frequency for LED control (1kHz default)
- Gamma correction for linear brightness perception
- Smooth brightness transitions
"""

import time
import threading
import math
from .jetson_gpio_manager import gpio_manager, GPIO


class JetsonEyesStable:
    """Improved LED PWM control with stable implementation"""
    
    def __init__(self, pin, frequency=1000):
        if GPIO is None:
            raise RuntimeError("Jetson.GPIO not available")
        
        # Validate pin is in the proven working set
        validated_pins = {7, 15, 29, 31, 32, 33}
        if pin not in validated_pins:
            raise ValueError(f"Pin {pin} not in validated pin set {validated_pins}")
            
        self.pin = pin
        self.frequency = frequency
        self.period_us = int(1_000_000 / frequency)  # Period in microseconds
        
        # State management
        self._duty_cycle = 0.0  # 0-100%
        self._target_brightness = 0.0  # 0-100%
        self._current_brightness = 0.0  # 0-100%
        self._pwm_running = False
        self._pwm_thread = None
        
        # Smooth transition parameters
        self.brightness_step = 2.0  # Change per cycle for smooth transitions
        self.gamma = 2.2  # Gamma correction for linear perception
        
        # Performance optimization
        self._cached_on_time_us = 0
        self._last_duty_cycle = -1
        
        # Initialize GPIO - LEDs start OFF
        gpio_manager.setup_pin(pin, GPIO.OUT, initial=GPIO.LOW)
        
        # Start PWM thread
        self._pwm_running = True
        self._pwm_thread = threading.Thread(target=self._pwm_worker, daemon=True)
        self._pwm_thread.start()
    
    def _apply_gamma_correction(self, brightness):
        """Apply gamma correction for linear brightness perception"""
        if brightness <= 0:
            return 0
        if brightness >= 100:
            return 100
        return (brightness / 100.0) ** self.gamma * 100.0
    
    def _smooth_brightness_transition(self):
        """Gradually change brightness to reduce LED flickering"""
        if abs(self._target_brightness - self._current_brightness) <= self.brightness_step:
            self._current_brightness = self._target_brightness
        else:
            # Move gradually towards target
            direction = 1 if self._target_brightness > self._current_brightness else -1
            self._current_brightness += direction * self.brightness_step
    
    def _pwm_worker(self):
        """High-precision PWM worker for LED control"""
        
        while self._pwm_running:
            try:
                # Smooth brightness transition
                self._smooth_brightness_transition()
                
                # Apply gamma correction
                corrected_brightness = self._apply_gamma_correction(self._current_brightness)
                
                # Update duty cycle only if changed (performance optimization)
                if corrected_brightness != self._last_duty_cycle:
                    self._duty_cycle = corrected_brightness
                    self._last_duty_cycle = corrected_brightness
                    
                    # Pre-calculate on time in microseconds
                    if self._duty_cycle > 0:
                        self._cached_on_time_us = int((self._duty_cycle / 100.0) * self.period_us)
                    else:
                        self._cached_on_time_us = 0
                
                # High-precision timing
                cycle_start = time.perf_counter()
                
                if self._cached_on_time_us > 0:
                    # ON phase
                    gpio_manager.output(self.pin, GPIO.HIGH)
                    
                    if self._cached_on_time_us < 1000:  # < 1ms, use busy wait
                        on_end = cycle_start + self._cached_on_time_us * 1e-6
                        while time.perf_counter() < on_end:
                            pass
                    else:  # > 1ms, use sleep + busy wait
                        sleep_time = (self._cached_on_time_us - 100) * 1e-6  # Sleep most of it
                        time.sleep(sleep_time)
                        on_end = cycle_start + self._cached_on_time_us * 1e-6
                        while time.perf_counter() < on_end:
                            pass
                    
                    # OFF phase
                    gpio_manager.output(self.pin, GPIO.LOW)
                    
                    # Wait for rest of period
                    off_time_us = self.period_us - self._cached_on_time_us
                    if off_time_us > 1000:  # > 1ms, use sleep + busy wait
                        sleep_time = (off_time_us - 100) * 1e-6
                        time.sleep(sleep_time)
                    
                    period_end = cycle_start + self.period_us * 1e-6
                    while time.perf_counter() < period_end:
                        pass
                else:
                    # LED is OFF - just maintain LOW and wait
                    gpio_manager.output(self.pin, GPIO.LOW)
                    time.sleep(self.period_us * 1e-6)
                        
            except RuntimeError:
                # GPIO pin was cleaned up, exit gracefully
                break
            except Exception:
                # Other errors, exit gracefully
                break
    
    def set_brightness(self, brightness):
        """Set target brightness 0-100%"""
        self._target_brightness = max(0, min(100, float(brightness)))
    
    def set_brightness_smooth(self, brightness, transition_speed=5.0):
        """Set brightness with smooth transition speed (steps per cycle)"""
        self.brightness_step = transition_speed
        self.set_brightness(brightness)
    
    def get_brightness(self):
        """Get current brightness level"""
        return self._current_brightness
    
    def is_changing(self):
        """Check if brightness is still transitioning"""
        return abs(self._current_brightness - self._target_brightness) > 0.1
    
    def pulse(self, min_brightness=5, max_brightness=100, steps=50, delay=0.02):
        """Create smooth pulsing effect"""
        original_step = self.brightness_step
        self.brightness_step = (max_brightness - min_brightness) / steps
        
        # Fade up
        self.set_brightness(max_brightness)
        while self.is_changing():
            time.sleep(delay)
        
        # Fade down  
        self.set_brightness(min_brightness)
        while self.is_changing():
            time.sleep(delay)
            
        # Restore original step size
        self.brightness_step = original_step
    
    def flash(self, duration=0.1, brightness=100):
        """Quick flash at specified brightness"""
        original_brightness = self._target_brightness
        original_step = self.brightness_step
        
        # Fast transition
        self.brightness_step = 100
        self.set_brightness(brightness)
        time.sleep(duration)
        self.set_brightness(original_brightness)
        
        # Restore original step
        self.brightness_step = original_step
    
    def update_frequency(self, frequency):
        """Update PWM frequency"""
        self.frequency = frequency
        self.period_us = int(1_000_000 / frequency)
    
    def get_stats(self):
        """Get performance statistics"""
        return {
            'frequency': self.frequency,
            'period_us': self.period_us,
            'current_brightness': self._current_brightness,
            'target_brightness': self._target_brightness,
            'duty_cycle': self._duty_cycle,
            'cached_on_time_us': self._cached_on_time_us,
            'is_changing': self.is_changing()
        }
    
    def cleanup(self):
        """Clean shutdown of PWM thread and GPIO"""
        # Stop PWM thread first, then cleanup GPIO
        self._pwm_running = False
        if self._pwm_thread and self._pwm_thread.is_alive():
            self._pwm_thread.join(timeout=1.0)
        
        # Turn off LED before cleanup
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