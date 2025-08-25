"""Simple PWM control for doll eyes (red LEDs)"""
import time
import threading
from .jetson_gpio_manager import gpio_manager, GPIO


class JetsonEyesPWM:
    def __init__(self, pin, frequency=1000):
        if GPIO is None:
            raise RuntimeError("Jetson.GPIO not available")
            
        self.pin = pin
        self.frequency = frequency
        self.period_s = 1.0 / frequency
        self._duty_cycle = 0.0  # 0-100%
        self._pwm_running = False
        
        gpio_manager.setup_pin(pin, GPIO.OUT, initial=GPIO.LOW)
        self._pwm_running = True
        self._pwm_thread = threading.Thread(target=self._pwm_worker, daemon=True)
        self._pwm_thread.start()
    
    def _pwm_worker(self):
        while self._pwm_running:
            if self._duty_cycle > 0:
                on_time = (self._duty_cycle / 100.0) * self.period_s
                off_time = self.period_s - on_time
                
                gpio_manager.output(self.pin, GPIO.HIGH)
                time.sleep(on_time)
                gpio_manager.output(self.pin, GPIO.LOW)
                time.sleep(off_time)
            else:
                gpio_manager.output(self.pin, GPIO.LOW)
                time.sleep(self.period_s)
    
    def set_brightness(self, brightness):
        """Set brightness 0-100%"""
        self._duty_cycle = max(0, min(100, brightness))
    
    def pulse(self, min_brightness=10, max_brightness=100, steps=20, delay=0.05):
        """Create pulsing effect"""
        step_size = (max_brightness - min_brightness) / steps
        
        # Fade up
        for i in range(steps):
            self.set_brightness(min_brightness + (i * step_size))
            time.sleep(delay)
        
        # Fade down  
        for i in range(steps):
            self.set_brightness(max_brightness - (i * step_size))
            time.sleep(delay)
    
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