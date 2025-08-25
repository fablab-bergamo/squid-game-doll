#!/usr/bin/env python3
"""
Independent test script for Jetson servo control.
Tests servo movement, limits, and calibration.

Usage:
    python test_jetson_servo.py
    
Controls:
    1 - Test single servo (H-axis)
    2 - Test single servo (V-axis) 
    3 - Test head servo
    4 - Test laser targeting system
    5 - Calibrate servo limits
    6 - Test laser on/off
    7 - Test eyes control
    8 - Full system test
    q - Quit
"""
import sys
import time
import select
import tty
import termios
from src.squid_game_doll.jetson_servo_simple import JetsonServoSimple
from src.squid_game_doll.jetson_laser_controller import JetsonLaserController
from src.squid_game_doll.jetson_gpio_manager import gpio_manager


class ServoTester:
    def __init__(self):
        self.controller = None
        self.single_servo = None
        self.running = False
    
    def init_controller(self):
        """Initialize laser controller system."""
        try:
            print("Initializing Jetson Laser Controller...")
            self.controller = JetsonLaserController(enable_laser=True)
            print("✓ Controller initialized successfully")
            return True
        except Exception as e:
            print(f"✗ Controller initialization failed: {e}")
            return False
    
    def test_single_servo(self, servo_type):
        """Test individual servo movement."""
        pin_map = {
            'h': JetsonLaserController.H_SERVO_PIN,    # Pin 33 (GPIO 13)
            'v': JetsonLaserController.V_SERVO_PIN,    # Pin 32 (GPIO 12)  
            'head': JetsonLaserController.HEAD_SERVO_PIN # Pin 18 (GPIO 24)
        }
        
        limit_map = {
            'h': (JetsonLaserController.H_MIN, JetsonLaserController.H_MAX),
            'v': (JetsonLaserController.V_MIN, JetsonLaserController.V_MAX),
            'head': (JetsonLaserController.HEAD_MIN, JetsonLaserController.HEAD_MAX)
        }
        
        pin = pin_map.get(servo_type)
        limits = limit_map.get(servo_type)
        
        if not pin or not limits:
            print(f"Invalid servo type: {servo_type}")
            return
        
        try:
            print(f"Testing {servo_type.upper()}-axis servo on pin {pin}")
            print(f"Limits: {limits[0]}° to {limits[1]}°")
            
            servo = JetsonServoSimple(pin)
            servo.update_settings(limits[0], limits[1])
            
            # Test sequence
            angles = [limits[0], limits[1], (limits[0] + limits[1]) / 2]
            
            for angle in angles:
                print(f"Moving to {angle}°...")
                servo.move(angle)
                time.sleep(2)
            
            print("Test complete. Returning to center...")
            servo.move((limits[0] + limits[1]) / 2)
            time.sleep(1)
            servo.cleanup()
            
        except Exception as e:
            print(f"Test failed: {e}")
    
    def test_targeting_system(self):
        """Test complete laser targeting system."""
        if not self.controller:
            if not self.init_controller():
                return
        
        print("Testing targeting system...")
        print("Moving to center position...")
        
        # Reset to center
        self.controller.reset_pos()
        time.sleep(2)
        
        # Test corner positions
        limits = self.controller.get_limits()
        positions = [
            (limits[0][0], limits[1][0]),  # Bottom-left
            (limits[0][1], limits[1][0]),  # Bottom-right  
            (limits[0][1], limits[1][1]),  # Top-right
            (limits[0][0], limits[1][1]),  # Top-left
            ((limits[0][0] + limits[0][1])/2, (limits[1][0] + limits[1][1])/2)  # Center
        ]
        
        position_names = ["Bottom-left", "Bottom-right", "Top-right", "Top-left", "Center"]
        
        for pos, name in zip(positions, position_names):
            print(f"Moving to {name}: H={pos[0]:.1f}°, V={pos[1]:.1f}°")
            self.controller.send_angles(pos)
            time.sleep(2)
        
        print("Targeting system test complete")
    
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
        """Test laser on/off control."""
        if not self.controller:
            if not self.init_controller():
                return
        
        print("Testing laser control...")
        print("WARNING: Ensure laser is pointed in a safe direction!")
        input("Press Enter to continue...")
        
        print("Laser ON for 2 seconds...")
        self.controller.set_laser(True)
        time.sleep(2)
        
        print("Laser OFF")
        self.controller.set_laser(False)
        
        print("Blinking test...")
        for i in range(5):
            self.controller.set_laser(True)
            time.sleep(0.2)
            self.controller.set_laser(False)
            time.sleep(0.2)
        
        print("Laser control test complete")
    
    def test_eyes_control(self):
        """Test doll eyes control."""
        if not self.controller:
            if not self.init_controller():
                return
        
        print("Testing eyes control...")
        
        print("Eyes ON for 3 seconds...")
        self.controller.set_eyes(True)
        time.sleep(3)
        
        print("Eyes OFF")
        self.controller.set_eyes(False)
        time.sleep(1)
        
        print("Blinking test...")
        for i in range(3):
            self.controller.set_eyes(True)
            time.sleep(0.5)
            self.controller.set_eyes(False)
            time.sleep(0.5)
        
        print("Eyes control test complete")
    
    def test_head_rotation(self):
        """Test head rotation for red/green light."""
        if not self.controller:
            if not self.init_controller():
                return
        
        print("Testing head rotation...")
        
        print("Green light - head turned away")
        self.controller.rotate_head(True)
        time.sleep(2)
        
        print("Red light - head facing forward")  
        self.controller.rotate_head(False)
        time.sleep(2)
        
        print("Alternating test...")
        for i in range(3):
            self.controller.rotate_head(True)
            time.sleep(1)
            self.controller.rotate_head(False)
            time.sleep(1)
        
        print("Head rotation test complete")
    
    def full_system_test(self):
        """Complete system functionality test."""
        if not self.controller:
            if not self.init_controller():
                return
        
        print("=== FULL SYSTEM TEST ===")
        
        # Test 1: Basic positioning
        print("1. Testing servo positioning...")
        self.test_targeting_system()
        time.sleep(1)
        
        # Test 2: Head rotation
        print("2. Testing head rotation...")
        self.test_head_rotation()
        time.sleep(1)
        
        # Test 3: Eyes control  
        print("3. Testing eyes...")
        self.test_eyes_control()
        time.sleep(1)
        
        # Test 4: Laser control (with safety check)
        response = input("Test laser control? (y/N): ").strip().lower()
        if response == 'y':
            self.test_laser_control()
        
        # Test 5: Simulated game sequence
        print("5. Simulating game sequence...")
        print("Green light phase...")
        self.controller.rotate_head(True)   # Head away
        self.controller.set_eyes(False)     # Eyes off
        time.sleep(2)
        
        print("Red light phase...")
        self.controller.rotate_head(False)  # Head forward
        self.controller.set_eyes(True)      # Eyes on
        time.sleep(2)
        
        # Reset all
        print("Resetting to safe state...")
        self.controller.set_laser(False)
        self.controller.set_eyes(False)
        self.controller.rotate_head(False)
        self.controller.reset_pos()
        
        print("=== FULL SYSTEM TEST COMPLETE ===")
    
    def run(self):
        """Main test loop."""
        print("Jetson Servo Test Suite")
        print("======================")
        
        while True:
            print("\nTest Options:")
            print("1 - Test H-axis servo")
            print("2 - Test V-axis servo")
            print("3 - Test head servo")
            print("4 - Test laser targeting system")
            print("5 - Calibrate servo limits")
            print("6 - Test laser on/off")
            print("7 - Test eyes control")
            print("8 - Full system test")
            print("q - Quit")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            try:
                if choice == '1':
                    self.test_single_servo('h')
                elif choice == '2':
                    self.test_single_servo('v')
                elif choice == '3':
                    self.test_single_servo('head')
                elif choice == '4':
                    self.test_targeting_system()
                elif choice == '5':
                    self.calibrate_limits()
                elif choice == '6':
                    self.test_laser_control()
                elif choice == '7':
                    self.test_eyes_control()
                elif choice == '8':
                    self.full_system_test()
                elif choice == 'q':
                    break
                else:
                    print("Invalid choice")
                    
            except KeyboardInterrupt:
                print("\nTest interrupted by user")
                break
            except Exception as e:
                print(f"Test error: {e}")
        
        # Cleanup
        if self.controller:
            print("Cleaning up...")
            self.controller.cleanup()
        
        # Final GPIO cleanup
        gpio_manager.cleanup_all()
        print("Test suite ended")


def main():
    """Main entry point."""
    try:
        tester = ServoTester()
        tester.run()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
    
    print("Goodbye!")


if __name__ == "__main__":
    main()