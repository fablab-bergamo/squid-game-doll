import asyncio
from head_controller import HeadController
from eyes_controller import EyesController
from laser_controller import LaserController
from test_mode_manager import TestModeManager
from status_led import StatusLED
from tracker_server import TrackerServer
from constants import *

async def main():
    print("ESP32 Tracker starting...")

    # Initialize controllers with constants
    head = HeadController(
        servo_pin=HEAD_SERVO_PIN,
        min_angle=HEAD_MIN,
        max_angle=HEAD_MAX,
        start_angle=HEAD_START_ANGLE
    )

    eyes = EyesController(pin=EYES_PIN)

    laser = LaserController(
        h_pin=H_SERVO_PIN,
        v_pin=V_SERVO_PIN,
        laser_pin=LASER_PIN,
        h_min=H_MIN,
        h_max=H_MAX,
        v_min=V_MIN,
        v_max=V_MAX,
        h_start=H_START_ANGLE,
        v_start=V_START_ANGLE
    )

    status_led = StatusLED(pin=INTEGRATED_RGB)
    test_manager = TestModeManager(head, eyes, laser, status_led)
    server = TrackerServer(head, eyes, laser, test_manager)

    # Start test mode initially (will run until first client connects)
    await test_manager.start_test_mode()

    # Create all background tasks
    tasks = [
        asyncio.create_task(head._positioning_task()),
        asyncio.create_task(head._test_rotation_task()),
        asyncio.create_task(eyes._pulse_task()),
        asyncio.create_task(laser._laser_blink_task()),
        asyncio.create_task(laser._tracking_task()),
        asyncio.create_task(laser._test_movement_task()),
        asyncio.create_task(status_led.blink_task()),
        asyncio.create_task(status_led.test_led_task()),
        asyncio.create_task(server.run_server())
    ]

    print("All systems initialized and running")
    print(f"Server will listen on {SERVER_HOST}:{SERVER_PORT}")
    print("Test mode active until first client connects")

    # Run all tasks concurrently
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Main error: {e}")
    finally:
        print("Tracker shutting down")
        asyncio.new_event_loop()