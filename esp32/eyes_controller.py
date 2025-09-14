import asyncio
from machine import Pin, PWM
from constants import PULSE_STEP_DELAY

class EyesController:
    def __init__(self, pin, freq=512):
        self.pwm = PWM(Pin(pin, Pin.OUT, drive=Pin.DRIVE_3), freq=freq)
        self.eyes_on = False
        self.test_active = False
        
    def set_brightness(self, duty):
        """Set the brightness of the LEDs using PWM duty cycle (0-1023)"""
        self.pwm.duty(duty)
        
    async def turn_on(self):
        """Turn eyes on (start pulsing)"""
        self.eyes_on = True
        
    async def turn_off(self):
        """Turn eyes off"""
        self.eyes_on = False
        self.set_brightness(0)
        
    async def start_test_mode(self):
        """Start test pulsing"""
        self.test_active = True
        self.eyes_on = True
        
    async def stop_test_mode(self):
        """Stop test mode"""
        self.test_active = False
        self.eyes_on = False
        
    async def _pulse_task(self):
        """Pulsing effect task"""
        step = 50
        while True:
            if not self.eyes_on:
                self.set_brightness(0)
                await asyncio.sleep_ms(PULSE_STEP_DELAY)
                continue
                
            # Gradually increase brightness
            for duty in range(0, 1024, step):
                if not self.eyes_on:
                    break
                self.set_brightness(duty)
                await asyncio.sleep_ms(PULSE_STEP_DELAY)
                
            # Gradually decrease brightness
            for duty in range(1023, 0, -step):
                if not self.eyes_on:
                    break
                self.set_brightness(duty)
                await asyncio.sleep_ms(PULSE_STEP_DELAY)