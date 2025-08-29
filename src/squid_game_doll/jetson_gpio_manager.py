"""
Jetson GPIO Manager - Simplified singleton for GPIO management
"""

import atexit
import logging
import os

# Fix for Jetson Orin Nano Super - Set model name before importing Jetson.GPIO
os.environ["JETSON_MODEL_NAME"] = "JETSON_ORIN_NANO"

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
            logger.debug("🚀 Initializing JetsonGPIOManager with proven configuration...")
            if GPIO is not None:
                logger.info("✅ Jetson.GPIO module available, setting up GPIO")
                try:
                    GPIO.setmode(GPIO.BOARD)
                    GPIO.setwarnings(True)
                    logger.info("✅ GPIO mode set to BOARD, warnings enabled")
                    atexit.register(self.cleanup_all)
                    logger.debug("🧹 Cleanup handler registered for exit")
                    JetsonGPIOManager._initialized = True
                    logger.info("✅ JetsonGPIOManager initialization complete")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize GPIO: {e}")
                    raise
            else:
                logger.warning("⚠️ Jetson.GPIO module not available - running in simulation mode")
                JetsonGPIOManager._initialized = True
        else:
            logger.debug("♻️ JetsonGPIOManager already initialized")

    def setup_pin(self, pin, mode, initial=None):
        logger.info(f"🔧 SETUP: Pin {pin} -> {mode} (initial={initial})")
        if GPIO is None:
            logger.error("❌ SETUP: Attempted to setup pin but Jetson.GPIO not available")
            raise RuntimeError("Jetson.GPIO not available")

        # Validate pin is in the proven working set
        validated_pins = {7, 15, 29, 31, 32, 33}
        if pin not in validated_pins:
            logger.warning(f"⚠️ SETUP: Pin {pin} not in validated pin set {validated_pins}")

        try:
            if initial is not None:
                GPIO.setup(pin, mode, initial=initial)
                logger.info(f"✅ SETUP: Pin {pin} configured as {mode} with initial value {initial}")
            else:
                GPIO.setup(pin, mode)
                logger.info(f"✅ SETUP: Pin {pin} configured as {mode}")
            self.used_pins.add(pin)
            logger.debug(f"📌 SETUP: Pin {pin} added to used_pins set. Used pins: {self.used_pins}")
        except Exception as e:
            logger.error(f"💥 SETUP: Exception on pin {pin}: {type(e).__name__}: {e}")
            raise

    def output(self, pin, value):
        if GPIO is not None:
            try:
                GPIO.output(pin, value)
                # Removed debug logging to reduce PWM noise
            except Exception as e:
                logger.error(f"💥 WRITE: Failed to write {'HIGH' if value else 'LOW'} to pin {pin}: {e}")
                raise
        else:
            logger.warning(f"⚠️ WRITE: Simulated write to pin {pin}: {'HIGH' if value else 'LOW'} (GPIO not available)")

    def cleanup_pin(self, pin):
        logger.debug(f"🧹 CLEANUP: Cleaning up pin {pin}")
        if GPIO is not None and pin in self.used_pins:
            try:
                GPIO.cleanup(pin)
                self.used_pins.discard(pin)
                logger.info(
                    f"✅ CLEANUP: Pin {pin} cleaned up and removed from used_pins. Remaining pins: {self.used_pins}"
                )
            except Exception as e:
                logger.error(f"💥 CLEANUP: Failed to cleanup pin {pin}: {e}")
                raise
        else:
            if GPIO is None:
                logger.debug(f"⚠️ CLEANUP: Skipping cleanup for pin {pin} - GPIO not available")
            elif pin not in self.used_pins:
                logger.warning(
                    f"⚠️ CLEANUP: Attempted to cleanup pin {pin} which was not in used_pins set: {self.used_pins}"
                )

    def cleanup_all(self):
        logger.debug(f"🧹 CLEANUP_ALL: Cleaning up all GPIO pins. Used pins: {self.used_pins}")
        if GPIO is not None and self.used_pins:
            try:
                GPIO.cleanup()
                logger.info(f"✅ CLEANUP_ALL: All GPIO pins cleaned up successfully. Cleaned pins: {self.used_pins}")
                self.used_pins.clear()
                logger.debug("🧹 CLEANUP_ALL: Used pins set cleared")
            except Exception as e:
                logger.error(f"💥 CLEANUP_ALL: Failed to cleanup all GPIO pins: {e}")
                raise
        else:
            if GPIO is None:
                logger.debug("⚠️ CLEANUP_ALL: Skipping cleanup_all - GPIO not available")
            else:
                logger.debug("ℹ️ CLEANUP_ALL: No pins to cleanup - used_pins set is empty")

    def get_pin_info(self):
        """Get information about all pins - following jetson-orin-webgpio pattern"""
        # Jetson Orin 40-pin GPIO header mapping (accurate JetsonHacks PDF pinout)
        all_pins = {
            # Physical pin: (type, description, gpio_number or None)
            1: ("power", "3.3 VDC Power", None),
            2: ("power", "5.0 VDC Power", None),
            3: ("gpio", "I2C1_SDA (I2C Bus 7)", None),  # I2C Bus 7, typically not used as GPIO
            4: ("power", "5.0 VDC Power", None),
            5: ("gpio", "I2C1_SCL (I2C Bus 7)", None),  # I2C Bus 7, typically not used as GPIO
            6: ("ground", "GND", None),
            7: ("gpio", "GPIO09 (AUDIO_MCLK)", 492),  # Sysfs: 144
            8: ("gpio", "UART1_TX (/dev/ttyTHS0)", None),  # /dev/ttyTHS0, typically not used as GPIO
            9: ("ground", "GND", None),
            10: ("gpio", "UART1_RX (/dev/ttyTHS0)", None),  # /dev/ttyTHS0, typically not used as GPIO
            11: ("gpio", "UART1_RTS", 460),  # Sysfs: 112
            12: ("gpio", "I2S0_SCLK", 398),  # Sysfs: 50
            13: ("gpio", "SPI1_SCK", 470),  # Sysfs: 122
            14: ("ground", "GND", None),
            15: ("gpio", "GPIO12 (Alt: PWM)", 433),  # Sysfs: 85
            16: ("gpio", "SPI1_CS1", 474),  # Sysfs: 126
            17: ("power", "3.3 VDC Power", None),
            18: ("gpio", "SPI1_CS0", 473),  # Sysfs: 125
            19: ("gpio", "SPI0_MOSI", 483),  # Sysfs: 135
            20: ("ground", "GND", None),
            21: ("gpio", "SPI0_MISO", 482),  # Sysfs: 134
            22: ("gpio", "SPI1_MISO", 471),  # Sysfs: 123
            23: ("gpio", "SPI0_SCK", 481),  # Sysfs: 133
            24: ("gpio", "SPI0_CS0", 484),  # Sysfs: 136
            25: ("ground", "GND", None),
            26: ("gpio", "SPI0_CS1", 485),  # Sysfs: 137
            27: ("gpio", "I2C0_SDA (I2C Bus 1)", None),  # I2C Bus 1, typically not used as GPIO
            28: ("gpio", "I2C0_SCL (I2C Bus 1)", None),  # I2C Bus 1, typically not used as GPIO
            29: ("gpio", "GPIO01", 453),  # Sysfs: 105
            30: ("ground", "GND", None),
            31: ("gpio", "GPIO11", 454),  # Sysfs: 106
            32: ("gpio", "GPIO07 (Alt: PWM)", 389),  # Sysfs: 41
            33: ("gpio", "GPIO13 (Alt: PWM)", 391),  # Sysfs: 43
            34: ("ground", "GND", None),
            35: ("gpio", "I2S0_FS", 401),  # Sysfs: 53
            36: ("gpio", "UART1_CTS", 461),  # Sysfs: 113
            37: ("gpio", "SPI1_MOSI", 472),  # Sysfs: 124
            38: ("gpio", "I2S0_SDIN", 400),  # Sysfs: 52
            39: ("ground", "GND", None),
            40: ("gpio", "I2S0_SDOUT", 399),  # Sysfs: 51
        }

        # Pins configured in gpio_pins.dts device tree overlay (validated working pins)
        dts_configured_pins = {7, 15, 29, 31, 32, 33}

        # GPIO pins that can be controlled (have GPIO numbers AND are configured in DTS)
        gpio_pins = {
            pin: gpio_num
            for pin, (pin_type, desc, gpio_num) in all_pins.items()
            if pin_type == "gpio" and gpio_num is not None and pin in dts_configured_pins
        }

        result = {}
        for pin, (pin_type, description, gpio_num) in all_pins.items():
            result[pin] = {
                "type": pin_type,
                "description": description,
                "gpio_num": gpio_num,
                "controllable": pin in gpio_pins,
                "dts_configured": pin in dts_configured_pins,
                "has_gpio_num": gpio_num is not None and pin_type == "gpio",
                "used": pin in self.used_pins,
            }

        return result


# Global GPIO manager instance
gpio_manager = JetsonGPIOManager()
