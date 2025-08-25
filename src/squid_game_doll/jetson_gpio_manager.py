"""
Jetson GPIO Manager - Simplified singleton for GPIO management
"""
import atexit
try:
    import Jetson.GPIO as GPIO
except ImportError:
    GPIO = None


class JetsonGPIOManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.used_pins = set()
        return cls._instance
    
    def __init__(self):
        if not self._initialized and GPIO is not None:
            GPIO.setmode(GPIO.BOARD)
            atexit.register(self.cleanup_all)
            JetsonGPIOManager._initialized = True
    
    def setup_pin(self, pin, mode, initial=None):
        if GPIO is None:
            raise RuntimeError("Jetson.GPIO not available")
        
        if initial is not None:
            GPIO.setup(pin, mode, initial=initial)
        else:
            GPIO.setup(pin, mode)
        self.used_pins.add(pin)
    
    def output(self, pin, value):
        if GPIO is not None:
            GPIO.output(pin, value)
    
    def cleanup_pin(self, pin):
        if GPIO is not None and pin in self.used_pins:
            GPIO.cleanup(pin)
            self.used_pins.discard(pin)
    
    def cleanup_all(self):
        if GPIO is not None and self.used_pins:
            GPIO.cleanup()


# Global GPIO manager instance
gpio_manager = JetsonGPIOManager()