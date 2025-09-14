import asyncio
import random
from machine import Pin
from Servo import Servo
from constants import LASER_BLINK_DELAY, TEST_MOVEMENT_DELAY

class LaserController:
    def __init__(self, h_pin, v_pin, laser_pin, h_min, h_max, v_min, v_max, h_start, v_start):
        self.h_servo = Servo(pin=h_pin)
        self.v_servo = Servo(pin=v_pin)
        self.laser = Pin(laser_pin, Pin.OUT)
        self.laser.value(1)  # Off by default (inverted logic)
        
        self.h_min = h_min
        self.h_max = h_max
        self.v_min = v_min
        self.v_max = v_max
        
        self.zero_position = (h_start, v_start)
        self.target_coord = self.zero_position
        self.force_off = True
        self.test_active = False
        
    async def set_target(self, h_angle, v_angle):
        """Set laser target coordinates"""
        h_clamped = max(self.h_min, min(self.h_max, h_angle))
        v_clamped = max(self.v_min, min(self.v_max, v_angle))
        self.target_coord = (h_clamped, v_clamped)
        
    async def laser_on(self):
        """Turn laser on"""
        self.force_off = False
        
    async def laser_off(self):
        """Turn laser off"""
        self.force_off = True
        self.laser.value(1)
        
    async def get_angles(self):
        """Get current servo angles"""
        return (round(self.h_servo.current_angle, 2), round(self.v_servo.current_angle, 2))
        
    async def get_limits(self):
        """Get servo angle limits"""
        return ((self.h_min, self.h_max), (self.v_min, self.v_max))
        
    async def start_test_mode(self):
        """Start test movement"""
        self.test_active = True
        
    async def stop_test_mode(self):
        """Stop test movement and return to zero"""
        self.test_active = False
        await self.set_target(*self.zero_position)
        
    async def _laser_blink_task(self):
        """Laser blinking task"""
        blink_state = True
        while True:
            if self.force_off:
                self.laser.value(1)  # Off
            else:
                self.laser.value(0 if blink_state else 1)  # Blink
            blink_state = not blink_state
            await asyncio.sleep_ms(LASER_BLINK_DELAY)
            
    async def _tracking_task(self):
        """Servo tracking task"""
        # Initialize to zero position
        self.h_servo.move(self.zero_position[0])
        self.v_servo.move(self.zero_position[1])
        await asyncio.sleep(2)
        
        h, v = self.zero_position
        
        while True:
            if self.target_coord is not None:
                h, v = self.target_coord
                self.h_servo.move(h)
                self.v_servo.move(v)
                self.target_coord = None
                await asyncio.sleep_ms(100)
            else:
                # Small random movements when no target
                h2 = h + random.uniform(-1.0, 1.0)
                v2 = v + random.uniform(-1.0, 1.0)
                h2 = max(self.h_min, min(self.h_max, h2))
                v2 = max(self.v_min, min(self.v_max, v2))
                self.h_servo.move(h2)
                self.v_servo.move(v2)
                await asyncio.sleep_ms(LASER_BLINK_DELAY)
                
    async def _test_movement_task(self):
        """Test movement pattern"""
        # Initialize to zero position
        h, v = self.zero_position
        self.h_servo.move(h)
        self.v_servo.move(v)
        await asyncio.sleep(2)
        
        delay = TEST_MOVEMENT_DELAY / 1000  # Convert ms to seconds
        range_h = list(range(self.h_min, self.h_max + 1))
        range_v = list(range(self.v_min, self.v_max + 1))
        
        while True:
            if not self.test_active:
                await asyncio.sleep_ms(100)
                continue
                
            # H axis forward
            for h in range_h:
                if not self.test_active:
                    break
                self.h_servo.move(h)
                await asyncio.sleep(delay)
            
            # V axis forward
            for v in range_v:
                if not self.test_active:
                    break
                self.v_servo.move(v)
                await asyncio.sleep(delay)
                
            # H axis reverse
            for h in reversed(range_h):
                if not self.test_active:
                    break
                self.h_servo.move(h)
                await asyncio.sleep(delay)
                
            # V axis reverse
            for v in reversed(range_v):
                if not self.test_active:
                    break
                self.v_servo.move(v)
                await asyncio.sleep(delay)