#!/usr/bin/env python3
"""
Jetson servo test - optimized version with 30s+ tests

Usage: python test_jetson_servo.py

1-H axis, 2-V axis, 3-Head, 4-Targeting, 5-Laser, 6-Eyes, 7-Full, q-Quit
"""
import time
import logging
from src.squid_game_doll.jetson_pwm import JetsonServoStable
from src.squid_game_doll.jetson_laser_controller import JetsonLaserController
from src.squid_game_doll.jetson_gpio_manager import gpio_manager

# Configure console logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Create logger for this script
logger = logging.getLogger(__name__)


class ServoTester:
    def __init__(self):
        self.controller = None
        self.single_servo = None
        self.running = False
    
    def init_controller(self):
        """Initialize laser controller system."""
        logger.info("Initializing Jetson Laser Controller system")
        try:
            print("Initializing Jetson Laser Controller...")
            self.controller = JetsonLaserController(enable_laser=True)
            logger.info("JetsonLaserController initialized successfully")
            print("✓ Controller initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Controller initialization failed: {e}")
            print(f"✗ Controller initialization failed: {e}")
            return False
    
    def test_single_servo(self, servo_type):
        """Test servo with 30s+ duration."""
        pins = {'h': 29, 'v': 31, 'head': 33}
        limits = {'h': (30, 150), 'v': (0, 120), 'head': (0, 180)}
        
        pin, lim = pins.get(servo_type), limits.get(servo_type)
        if not pin:
            print(f"Invalid servo: {servo_type}")
            return
        
        try:
            print(f"Testing {servo_type} servo (30s sweep test)")
            servo = JetsonServoStable(pin, min_angle=lim[0], max_angle=lim[1])
            
            # 30+ second continuous sweep test
            start_time = time.time()
            while time.time() - start_time < 35:
                # Sweep back and forth
                for angle in [lim[0], lim[1], (lim[0]+lim[1])/2]:
                    servo.move(angle)
                    time.sleep(3)
                    print(f"{servo_type}: {angle:.0f}° ({time.time()-start_time:.1f}s)")
                    if time.time() - start_time >= 35:
                        break
            
            servo.move((lim[0]+lim[1])/2)  # Center
            time.sleep(1)
            servo.cleanup()
            print(f"{servo_type} test complete")
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    def test_targeting_system(self):
        """30s+ targeting pattern test."""
        if not self.controller:
            if not self.init_controller():
                return
        
        print("Targeting system test (30s pattern)")
        positions = [(30,0), (150,0), (150,120), (30,120), (90,60)]  # Square + center
        names = ["BL", "BR", "TR", "TL", "Center"]
        
        start_time = time.time()
        cycles = 0
        while time.time() - start_time < 32:
            for pos, name in zip(positions, names):
                self.controller.send_angles(pos)
                time.sleep(2.5)
                print(f"{name}: H={pos[0]}, V={pos[1]} ({time.time()-start_time:.1f}s)")
                if time.time() - start_time >= 32:
                    break
            cycles += 1
        
        self.controller.reset_pos()
        print(f"Targeting complete - {cycles} cycles")
    
    def calibrate_limits(self):
        """Interactive servo limit calibration."""
        print("Servo Limit Calibration")
        print("Use arrow keys to move servos, 's' to save position, 'q' to quit")
        
        if not self.controller:
            if not self.init_controller():
                return
        
        # Set terminal to non-blocking input
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin)
            
            current_h, current_v = self.controller.get_angles()
            step = 1.0
            
            print(f"Current position: H={current_h:.1f}°, V={current_v:.1f}°")
            print("Controls: ←→ (H-axis), ↑↓ (V-axis), +/- (step size), 'q' (quit)")
            
            while True:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1).lower()
                    
                    if key == 'q':
                        break
                    elif key == '\x1b':  # Arrow key sequence
                        key2 = sys.stdin.read(1)
                        key3 = sys.stdin.read(1)
                        if key2 == '[':
                            if key3 == 'A':    # Up arrow
                                current_v = min(current_v + step, JetsonLaserController.V_MAX)
                            elif key3 == 'B':  # Down arrow
                                current_v = max(current_v - step, JetsonLaserController.V_MIN)
                            elif key3 == 'C':  # Right arrow
                                current_h = min(current_h + step, JetsonLaserController.H_MAX)
                            elif key3 == 'D':  # Left arrow
                                current_h = max(current_h - step, JetsonLaserController.H_MIN)
                    elif key == '+':
                        step = min(step * 2, 10.0)
                        print(f"Step size: {step}°")
                        continue
                    elif key == '-':
                        step = max(step / 2, 0.1)
                        print(f"Step size: {step}°")
                        continue
                    elif key == 's':
                        print(f"Saved position: H={current_h:.1f}°, V={current_v:.1f}°")
                        continue
                    else:
                        continue
                    
                    self.controller.send_angles((current_h, current_v))
                    print(f"Position: H={current_h:.1f}°, V={current_v:.1f}°", end='\r')
                    
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            print("\nCalibration complete")
    
    def test_laser_control(self):
        """30s laser pattern test."""
        if not self.controller:
            if not self.init_controller():
                return
        
        print("Laser control test (30s patterns)")
        input("WARNING: Point laser safely! Press Enter...")
        
        patterns = [
            ("Solid 5s", [(True, 5)]),
            ("Fast blink", [(True, 0.2), (False, 0.2)] * 10),
            ("Slow pulse", [(True, 1), (False, 1)] * 5),
            ("Morse SOS", [(True, 0.2), (False, 0.2)] * 3 + [(True, 0.6), (False, 0.2)] * 3 + [(True, 0.2), (False, 0.2)] * 3),
        ]
        
        for name, pattern in patterns:
            print(f"{name}...")
            for state, duration in pattern:
                self.controller.set_laser(state)
                time.sleep(duration)
        
        self.controller.set_laser(False)
        print("Laser test complete")
    
    def test_eyes_control(self):
        """30s eyes pattern test."""
        if not self.controller:
            if not self.init_controller():
                return
        
        print("Eyes control test (30s patterns)")
        
        # Brightness levels test (10s)
        for brightness in [25, 50, 75, 100]:
            print(f"Brightness {brightness}%")
            self.controller.eyes_pwm.set_brightness(brightness)
            time.sleep(2.5)
        
        # Pulsing patterns (20s)
        print("Pulsing patterns...")
        for _ in range(4):
            self.controller.eyes_pwm.pulse(min_brightness=10, max_brightness=90, steps=15, delay=0.15)
            time.sleep(1)
        
        self.controller.set_eyes(False)
        print("Eyes test complete")
    
    
    def full_system_test(self):
        """60s full system test."""
        if not self.controller:
            if not self.init_controller():
                return
        
        print("=== FULL SYSTEM TEST (60s) ===")
        
        # Game simulation sequence (30s)
        for cycle in range(3):
            print(f"Game cycle {cycle+1}/3")
            
            # Green light (10s)
            print("GREEN LIGHT")
            self.controller.rotate_head(True)  # Head away
            self.controller.set_eyes(False)
            for i in range(4):
                pos = [(30,0), (150,0), (150,120), (30,120)][i]
                self.controller.send_angles(pos)
                time.sleep(2.5)
            
            # Red light (10s)
            print("RED LIGHT")
            self.controller.rotate_head(False)  # Head forward
            self.controller.set_eyes(True)
            time.sleep(5)
            
            # Laser test (optional)
            if cycle == 1:
                response = input("Test laser? (y/N): ").strip().lower()
                if response == 'y':
                    self.controller.set_laser(True)
                    time.sleep(2)
                    self.controller.set_laser(False)
            else:
                time.sleep(2)
        
        # Reset
        self.controller.set_laser(False)
        self.controller.set_eyes(False)
        self.controller.rotate_head(False)
        self.controller.reset_pos()
        print("=== FULL TEST COMPLETE ===")
    
    def run(self):
        """Main test loop."""
        logger.info("Starting Jetson Servo Test Suite")
        print("Jetson Servo Test Suite")
        print("======================")
        
        while True:
            print("\n1-H servo, 2-V servo, 3-Head, 4-Targeting, 5-Laser, 6-Eyes, 7-Full, q-Quit")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            try:
                if choice == '1':
                    logger.info("User selected: Test H-axis servo")
                    self.test_single_servo('h')
                elif choice == '2':
                    logger.info("User selected: Test V-axis servo")
                    self.test_single_servo('v')
                elif choice == '3':
                    logger.info("User selected: Test head servo")
                    self.test_single_servo('head')
                elif choice == '4':
                    logger.info("User selected: Test laser targeting system")
                    self.test_targeting_system()
                elif choice == '5':
                    logger.info("User selected: Test laser control")
                    self.test_laser_control()
                elif choice == '6':
                    logger.info("User selected: Test eyes control")
                    self.test_eyes_control()
                elif choice == '7':
                    logger.info("User selected: Full system test")
                    self.full_system_test()
                elif choice == 'q':
                    logger.info("User selected: Quit")
                    break
                else:
                    logger.warning(f"User entered invalid choice: {choice}")
                    print("Invalid choice")
                    
            except KeyboardInterrupt:
                logger.warning("Test interrupted by user (Ctrl+C)")
                print("\nTest interrupted by user")
                break
            except Exception as e:
                logger.error(f"Test execution error: {e}")
                print(f"Test error: {e}")
        
        # Cleanup
        logger.info("Starting cleanup process")
        if self.controller:
            print("Cleaning up...")
            logger.debug("Cleaning up JetsonLaserController")
            self.controller.cleanup()
        
        # Final GPIO cleanup
        logger.debug("Performing final GPIO cleanup")
        gpio_manager.cleanup_all()
        logger.info("Test suite ended successfully")
        print("Test suite ended")


def main():
    """Main entry point."""
    logger.info("=== JETSON SERVO TEST SUITE STARTED ===")
    try:
        tester = ServoTester()
        tester.run()
    except KeyboardInterrupt:
        logger.warning("Program interrupted by user (Ctrl+C)")
        print("\nProgram interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error occurred: {e}")
        print(f"Fatal error: {e}")
    
    logger.info("=== JETSON SERVO TEST SUITE FINISHED ===")
    print("Goodbye!")


if __name__ == "__main__":
    main()