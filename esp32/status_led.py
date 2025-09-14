import asyncio
import neopixel
from machine import Pin
from constants import STATUS_BLINK_DELAY

class StatusLED:
    def __init__(self, pin):
        self.np = neopixel.NeoPixel(Pin(pin), 1)
        
    async def blink_task(self):
        """Status LED blinking task"""
        import network
        wlan = network.WLAN(network.STA_IF)
        
        while True:
            if wlan.isconnected():
                self.np[0] = (0, 16, 0)  # Green for connected
            else:
                self.np[0] = (16, 0, 0)  # Red for disconnected
            self.np.write()
            await asyncio.sleep_ms(STATUS_BLINK_DELAY)
            self.np[0] = (0, 0, 0)
            self.np.write()
            await asyncio.sleep_ms(STATUS_BLINK_DELAY)