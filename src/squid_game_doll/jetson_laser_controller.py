"""Minimal Jetson Laser Controller - Essential functionality only"""
import time
import numpy as np
from numpy.linalg import norm
from .jetson_servo_simple import JetsonServoSimple
from .jetson_eyes_pwm import JetsonEyesPWM
from .jetson_gpio_manager import gpio_manager, GPIO


class JetsonLaserController:
    # Pin assignments
    H_SERVO_PIN = 33; V_SERVO_PIN = 15; HEAD_SERVO_PIN = 32
    LASER_PIN = 29; EYES_PIN = 16
    
    # Angle limits
    H_MIN = 30; H_MAX = 150; V_MIN = 0; V_MAX = 120
    HEAD_MIN = 0; HEAD_MAX = 180
    
    def __init__(self, deadband_px=10, max_frequency_hz=10, enable_laser=True):
        self.deadband = deadband_px
        self.min_period_S = 1.0 / max_frequency_hz
        self._enable_laser = enable_laser
        self.last_sent = 0
        self.coeffs = (50.0, 15.0)
        
        # Initialize hardware
        gpio_manager.setup_pin(self.LASER_PIN, GPIO.OUT, initial=GPIO.HIGH)
        
        self.motor_h = JetsonServoSimple(self.H_SERVO_PIN)
        self.motor_v = JetsonServoSimple(self.V_SERVO_PIN)
        self.motor_head = JetsonServoSimple(self.HEAD_SERVO_PIN)
        self.eyes_pwm = JetsonEyesPWM(self.EYES_PIN)
        
        self.motor_h.update_settings(self.H_MIN, self.H_MAX)
        self.motor_v.update_settings(self.V_MIN, self.V_MAX)
        self.motor_head.update_settings(self.HEAD_MIN, self.HEAD_MAX)
        
        self.reset_pos()
        self._is_online = True
    
    def is_laser_enabled(self): return self._enable_laser
    def isOnline(self): return self._is_online
    def set_coeffs(self, px_per_degree): 
        if px_per_degree: self.coeffs = px_per_degree
    
    def get_limits(self): return ((self.H_MIN, self.H_MAX), (self.V_MIN, self.V_MAX))
    def get_angles(self): return (self.motor_h.current_angle, self.motor_v.current_angle)
    
    def send_angles(self, angles):
        h, v = angles
        h = max(self.H_MIN, min(self.H_MAX, h))
        v = max(self.V_MIN, min(self.V_MAX, v))
        self.motor_h.move(h)
        self.motor_v.move(v)
        return True
    
    def reset_pos(self):
        h = (self.H_MIN + self.H_MAX) / 2
        v = (self.V_MIN + self.V_MAX) / 2
        return self.send_angles((h, v))
    
    def set_laser(self, on_or_off):
        if self._enable_laser:
            gpio_manager.output(self.LASER_PIN, GPIO.LOW if on_or_off else GPIO.HIGH)
        return True
    
    def rotate_head(self, green_light):
        self.motor_head.move(self.HEAD_MAX if green_light else self.HEAD_MIN)
        return True
    
    def set_eyes(self, eyes_on):
        if eyes_on:
            self.eyes_pwm.set_brightness(50)  # 50% brightness when on
        else:
            self.eyes_pwm.set_brightness(0)   # Off
        return True
    
    def track_target(self, laser, target):
        if not (laser and target): return 0
        
        error = norm(np.array(laser) - np.array(target))
        v_err = laser[1] - target[1]
        h_err = laser[0] - target[0]
        
        up = v_err < -self.deadband
        down = v_err > self.deadband
        left = h_err > self.deadband  
        right = h_err < -self.deadband
        
        step_v = min(max(0.8, abs(v_err / self.coeffs[1])), 20)
        step_h = min(max(0.8, abs(h_err / self.coeffs[0])), 20)
        
        self.send_instructions(up, down, left, right, step_v, step_h)
        return error
    
    def send_instructions(self, up, down, left, right, step_v, step_h):
        if time.time() - self.last_sent < self.min_period_S:
            return True
        self.last_sent = time.time()
        
        h, v = self.get_angles()
        if up: v += step_v
        if down: v -= step_v
        if left: h += step_h
        if right: h -= step_h
        
        return self.send_angles((h, v))
    
    def cleanup(self):
        self.set_laser(False)
        self.set_eyes(False)
        self.motor_h.cleanup()
        self.motor_v.cleanup()
        self.motor_head.cleanup()
        self.eyes_pwm.cleanup()
        gpio_manager.cleanup_pin(self.LASER_PIN)
        self._is_online = False
    
    def __del__(self):
        try: self.cleanup()
        except: pass