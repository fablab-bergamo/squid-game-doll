import asyncio


class TestModeManager:
    def __init__(self, head_controller, eyes_controller, laser_controller):
        self.head = head_controller
        self.eyes = eyes_controller
        self.laser = laser_controller
        self.test_mode_active = True  # Start in test mode
        self.client_count = 0

    async def start_test_mode(self):
        """Start all test modes"""
        print("Starting test mode...")
        self.test_mode_active = True
        await asyncio.sleep(5)
        if self.test_mode_active:
            await self.head.start_test_mode()
            await self.eyes.start_test_mode()
            await self.laser.start_test_mode()

    async def stop_test_mode(self):
        """Stop all test modes and set default state"""
        print("Stopping test mode...")
        self.test_mode_active = False
        await self.head.stop_test_mode()
        await self.eyes.stop_test_mode()
        await self.laser.stop_test_mode()

        await asyncio.sleep(2)

        # Set default state
        await self.head.get_position_0()  # Head forward
        await self.eyes.turn_off()  # Eyes off
        await self.laser.laser_off()  # Laser off

    async def on_client_connect(self):
        """Handle client connection"""
        self.client_count += 1
        print(f"Client connected, count: {self.client_count}")
        if self.client_count == 1 and self.test_mode_active:
            print("First client connected, stopping test mode")
            await self.stop_test_mode()

    async def on_client_disconnect(self):
        """Handle client disconnection"""
        if self.client_count > 0:
            self.client_count -= 1
        print(f"Client disconnected, count: {self.client_count}")
        if self.client_count == 0 and not self.test_mode_active:
            print("No clients connected, restarting test mode")
            await self.start_test_mode()
