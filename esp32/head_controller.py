import asyncio
from Servo import Servo
from constants import SERVO_STEP_DELAY

class HeadController:
    def __init__(self, servo_pin, min_angle, max_angle, start_angle):
        self.servo = Servo(pin=servo_pin)
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.target_position = start_angle
        self.test_active = False
        
    async def set_position(self, angle):
        """Set target head position"""
        self.target_position = max(self.min_angle, min(self.max_angle, angle))
        
    async def get_position_0(self):
        """Move to position 0 (forward)"""
        await self.set_position(self.min_angle)
        
    async def get_position_1(self):
        """Move to position 1 (turned away)"""
        await self.set_position(self.max_angle)
        
    async def start_test_mode(self):
        """Start test head rotation"""
        self.test_active = True
        
    async def stop_test_mode(self):
        """Stop test head rotation"""
        self.test_active = False
        
    async def _positioning_task(self):
        """Smooth positioning task"""
        while True:
            current = int(self.servo.current_angle)
            target = int(self.target_position)
            
            if current != target:
                if current > target:
                    self.servo.move(target)
                else:
                    for angle in range(current, target, 2):
                        self.servo.move(angle)
                        await asyncio.sleep_ms(SERVO_STEP_DELAY)
                        if int(self.target_position) != target:
                            break
            await asyncio.sleep_ms(50)
            
    async def _test_rotation_task(self):
        """Test rotation movement"""
        await asyncio.sleep(1)  # Initial delay
        while True:
            if not self.test_active:
                await asyncio.sleep_ms(100)
                continue
                
            # Smooth sweep from min to max
            for angle in range(self.min_angle, self.max_angle + 1, 1):
                if not self.test_active:
                    break
                self.servo.move(angle)
                await asyncio.sleep_ms(5)
            await asyncio.sleep(2)
            
            # Smooth sweep from max to min
            for angle in range(self.max_angle, self.min_angle - 1, -1):
                if not self.test_active:
                    break
                self.servo.move(angle)
                await asyncio.sleep_ms(5)
            await asyncio.sleep(2)