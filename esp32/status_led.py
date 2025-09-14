import asyncio
import neopixel
from machine import Pin
from constants import STATUS_BLINK_DELAY


class StatusLED:
    def __init__(self, pin):
        self.np = neopixel.NeoPixel(Pin(pin), 1)
        self.test_active = False

    async def start_test_mode(self):
        """Start LED test"""
        self.test_active = True

    async def stop_test_mode(self):
        """Stop LED test"""
        self.test_active = False
        # Turn off LED when stopping test mode
        self.np[0] = (0, 0, 0)
        self.np.write()

    async def test_led_task(self):
        """LED test mode task - cycles through RGB colors"""
        while True:
            if not self.test_active:
                await asyncio.sleep_ms(100)
                continue

            # Cycle through Red, Green, Blue for 0.5 seconds each
            for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
                if not self.test_active:
                    break
                self.np[0] = color
                self.np.write()
                await asyncio.sleep_ms(500)

            # Turn off for 2 seconds
            self.np[0] = (0, 0, 0)
            self.np.write()
            await asyncio.sleep(2)

    async def blink_task(self):
        """Status LED blinking task - shows WiFi connection status"""
        import network
        wlan = network.WLAN(network.STA_IF)

        while True:
            # Skip WiFi indication during test mode
            if self.test_active:
                await asyncio.sleep_ms(STATUS_BLINK_DELAY)
                continue

            if wlan.isconnected():
                self.np[0] = (0, 16, 0)  # Green for connected
            else:
                self.np[0] = (16, 0, 0)  # Red for disconnected
            self.np.write()
            await asyncio.sleep_ms(STATUS_BLINK_DELAY)
            self.np[0] = (0, 0, 0)
            self.np.write()
            await asyncio.sleep_ms(STATUS_BLINK_DELAY)