"""
Jetson GPIO Manager - Simplified singleton for GPIO management
"""

import atexit
import logging

try:
    import Jetson.GPIO as GPIO
except ImportError:
    GPIO = None

# Configure logger for GPIO operations
logger = logging.getLogger(__name__)


class JetsonGPIOManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            logger.debug("Creating new JetsonGPIOManager singleton instance")
            cls._instance = super().__new__(cls)
            cls._instance.used_pins = set()
            logger.debug("JetsonGPIOManager singleton instance created")
        else:
            logger.debug("Returning existing JetsonGPIOManager singleton instance")
        return cls._instance

    def __init__(self):
        if not self._initialized:
            logger.debug("Initializing JetsonGPIOManager")
            if GPIO is not None:
                logger.info("Jetson.GPIO module available, setting up GPIO")
                GPIO.setmode(GPIO.BOARD)
                logger.debug("GPIO mode set to BOARD")
                atexit.register(self.cleanup_all)
                logger.debug("Cleanup handler registered for exit")
                JetsonGPIOManager._initialized = True
                logger.info("JetsonGPIOManager initialization complete")
            else:
                logger.warning("Jetson.GPIO module not available - running in simulation mode")
                JetsonGPIOManager._initialized = True
        else:
            logger.debug("JetsonGPIOManager already initialized")

    def setup_pin(self, pin, mode, initial=None):
        logger.debug(f"Setting up pin {pin} with mode {mode}, initial={initial}")
        if GPIO is None:
            logger.error("Attempted to setup pin but Jetson.GPIO not available")
            raise RuntimeError("Jetson.GPIO not available")

        try:
            if initial is not None:
                GPIO.setup(pin, mode, initial=initial)
                logger.info(f"Pin {pin} configured as {mode} with initial value {initial}")
            else:
                GPIO.setup(pin, mode)
                logger.info(f"Pin {pin} configured as {mode}")
            self.used_pins.add(pin)
            logger.debug(f"Pin {pin} added to used_pins set. Used pins: {self.used_pins}")
        except Exception as e:
            logger.error(f"Failed to setup pin {pin}: {e}")
            raise

    def output(self, pin, value):
        if GPIO is not None:
            try:
                GPIO.output(pin, value)
            except Exception as e:
                logger.error(f"Failed to write {value} to pin {pin}: {e}")
                raise
        else:
            logger.warning(f"Simulated write to pin {pin}: {value} (GPIO not available)")

    def cleanup_pin(self, pin):
        logger.debug(f"Cleaning up pin {pin}")
        if GPIO is not None and pin in self.used_pins:
            try:
                GPIO.cleanup(pin)
                self.used_pins.discard(pin)
                logger.info(f"Pin {pin} cleaned up and removed from used_pins. Remaining pins: {self.used_pins}")
            except Exception as e:
                logger.error(f"Failed to cleanup pin {pin}: {e}")
                raise
        else:
            if GPIO is None:
                logger.debug(f"Skipping cleanup for pin {pin} - GPIO not available")
            elif pin not in self.used_pins:
                logger.warning(f"Attempted to cleanup pin {pin} which was not in used_pins set: {self.used_pins}")

    def cleanup_all(self):
        logger.debug(f"Cleaning up all GPIO pins. Used pins: {self.used_pins}")
        if GPIO is not None and self.used_pins:
            try:
                GPIO.cleanup()
                logger.info(f"All GPIO pins cleaned up successfully. Cleaned pins: {self.used_pins}")
                self.used_pins.clear()
                logger.debug("Used pins set cleared")
            except Exception as e:
                logger.error(f"Failed to cleanup all GPIO pins: {e}")
                raise
        else:
            if GPIO is None:
                logger.debug("Skipping cleanup_all - GPIO not available")
            else:
                logger.debug("No pins to cleanup - used_pins set is empty")


# Global GPIO manager instance
gpio_manager = JetsonGPIOManager()
