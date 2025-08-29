"""Simple Jetson Servo Control with software PWM"""
import time
import threading
from .jetson_gpio_manager import gpio_manager, GPIO


class JetsonServoSimple:
    def __init__(self, pin):
        if GPIO is None:
            raise RuntimeError("Jetson.GPIO not available")
        
        # Validate pin is in the proven working set
        validated_pins = {7, 15, 29, 31, 32, 33}
        if pin not in validated_pins:
            raise ValueError(f"Pin {pin} not in validated pin set {validated_pins}")
            
        self.pin = pin
        self.current_angle = 90.0
        self.min_angle = 0.0
        self.max_angle = 180.0
        self._target_angle = 90.0
        self._pwm_running = False
        
        # Set pin LOW initially, then start PWM
        gpio_manager.setup_pin(pin, GPIO.OUT, initial=GPIO.LOW)
        self._pwm_running = True
        self._pwm_thread = threading.Thread(target=self._pwm_worker, daemon=True)
        self._pwm_thread.start()
        # Move to center position (90 degrees)
        self.move(90.0)
    
    def _pwm_worker(self):
        period_s = 0.02  # 20ms for 50Hz
        while self._pwm_running:
            # Convert angle to pulse width (0.5ms to 2.5ms for SG90)
            angle = max(self.min_angle, min(self.max_angle, self._target_angle))
            pulse_ms = 0.5 + (angle / 180.0) * 2.0
            pulse_s = pulse_ms / 1000.0
            
            gpio_manager.output(self.pin, GPIO.HIGH)
            time.sleep(pulse_s)
            gpio_manager.output(self.pin, GPIO.LOW)
            time.sleep(period_s - pulse_s)
    
    def move(self, angle):
        self._target_angle = max(self.min_angle, min(self.max_angle, round(angle, 1)))
        self.current_angle = self._target_angle
    
    def update_settings(self, min_angle, max_angle):
        self.min_angle = min_angle  
        self.max_angle = max_angle
    
    def cleanup(self):
        self._pwm_running = False
        if self._pwm_thread and self._pwm_thread.is_alive():
            self._pwm_thread.join(timeout=0.1)
        gpio_manager.cleanup_pin(self.pin)
    
    def __del__(self):
        try:
            self.cleanup()
        except:
            pass