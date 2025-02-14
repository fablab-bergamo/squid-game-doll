from numpy.linalg import norm
import numpy as np
import socket
from time import time
from simple_pid import PID

class TrackerControl:
    def __init__(self, ipaddress:str, deadband_px:int = 10):
        self.is_online = False
        self.ip_address = ipaddress
        self.port = 15555
        self.aliensocket = None
        self.last_sent = 0
        self.limits = self.get_limits()
        self.pid_ok = self.init_PID()
        self.deadband = deadband_px

    def init_PID(self) -> bool:
        if self.limits is not None:
            start_v = (self.limits[1][1] - self.limits[1][0]) / 2
            start_h = (self.limits[0][1] - self.limits[0][0]) / 2
            self.pid_v = PID(0.01, 0.005, 0.002, setpoint=0, output_limits=(self.limits[1][0],self.limits[1][1]), starting_output=start_v)
            self.pid_h = PID(0.01, 0.005, 0.002, setpoint=0, output_limits=(self.limits[0][0],self.limits[0][1]), starting_output=start_h)
            self.pid_h.sample_time = 0.5
            self.pid_v.sample_time = 0.5
            self.send_angles((start_h, start_v))
            self.prev_output_h = start_h
            self.prev_output_v = start_v
            return True
        
        print("PID init failure")
        return False

    def isOnline(self) -> bool:
        return self.is_online

    def track_target(self, laser:tuple, target:tuple) -> float:
        """
        Tracks the target position relative to the laser position and provides feedback.

        Parameters:
        laser (tuple): The (x, y) coordinates of the laser position.
        target (tuple): The (x, y) coordinates of the target position.

        Returns:
        float: The positioning error in absolute distance.
        """
        # compute the positionning error in abs distance
        if target is None or laser is None:
            return 0
        
        error = norm(np.array(laser) - np.array(target))

        vertical_error = laser[0] - target[0]
        horizontal_error = laser[1] - target[1]

        up = False
        down = False
        left = False
        right = False

        if vertical_error < -1 * self.deadband:
            up = True
        elif vertical_error > self.deadband:
            down = True

        if horizontal_error < -1 * self.deadband:
            left = True
        elif horizontal_error > self.deadband:
            right = True

        step_v = min(max(0.4, abs(vertical_error / 100.0)), 10)
        step_h = min(max(0.5, abs(horizontal_error / 100.0)), 10)

        print(f"-> Step V {step_v}, step H {step_h}")

        self.send_instructions(up, down, left, right, step_v, step_h)
        # Send the updated angles to ESP32
        return error


    def track_target_PID(self, laser:tuple, target:tuple) -> float:
        """
        Tracks the target position relative to the laser position and provides feedback.

        Parameters:
        laser (tuple): The (x, y) coordinates of the laser position.
        target (tuple): The (x, y) coordinates of the target position.

        Returns:
        float: The positioning error in absolute distance.
        """
        RATE_OF_CHANGE = 1

        if not self.pid_ok:
            self.pid_ok = self.init_PID()
            if not self.pid_ok:
                return 0.0

        # compute the positionning error in abs distance
        if target is None or laser is None:
            return 0
        
        error = norm(np.array(laser) - np.array(target))

        vertical_error = -(laser[0] - target[0])
        horizontal_error = -(laser[1] - target[1])

        output_h = self.pid_h(horizontal_error)
        output_v = self.pid_v(vertical_error)

        if abs(output_h - self.prev_output_h) > RATE_OF_CHANGE:
            print(f"Rate limiting H from {output_h} to {RATE_OF_CHANGE}")
            if (output_h > self.prev_output_h):
                output_h = self.prev_output_h + RATE_OF_CHANGE
            else:
                output_h = self.prev_output_h - RATE_OF_CHANGE
        
        if abs(output_v - self.prev_output_v) > RATE_OF_CHANGE:
            print(f"Rate limiting V from {output_v} to {RATE_OF_CHANGE}")
            if (output_v > self.prev_output_v):
                output_v = self.prev_output_v + RATE_OF_CHANGE
            else:
                output_v = self.prev_output_v - RATE_OF_CHANGE
            

        self.prev_output_h = output_h
        self.prev_output_v = output_v

        self.send_angles((output_h, output_v))

        return error

    def reset_pos(self):
        self.send_angles(self.DEFAULT_POS)
        self.current_pos = self.DEFAULT_POS

    def get_angles(self) -> tuple:
        data = bytes("?", "utf-8")
        try:
            self.aliensocket.sendall(data)
            response = self.aliensocket.recv()
            self.is_online = True
            return eval(response)
        except:
            print("get_angles: failure to contact ESP32")
            self.aliensocket = None
            self.is_online = False
            return None

    def get_limits(self) -> tuple:
        data = bytes("limits", "utf-8")
        try:
            self.aliensocket.sendall(data)
            response = self.aliensocket.recv()
            self.is_online = True
            return eval(response)
        except:
            print("get_angles: failure to contact ESP32")
            self.aliensocket = None
            self.is_online = False
            return None
        
    def send_angles(self, angles:tuple) -> bool:
        print(f"send_angles: target (H,V)=({angles[0]}, {angles[1]})")
        
        if self.aliensocket is None:
            self.aliensocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                print(f"send_angles: connecting to {self.ip_address}:{self.port}")
                self.aliensocket.settimeout(0.5)
                self.aliensocket.connect((self.ip_address, self.port))
            except:
                print("send_angles: failure to connect!")
                self.is_online = False
                return False

        data = bytes(str((angles[1], angles[0])), "utf-8")
        try:
            self.aliensocket.send(data)
            self.is_online = True
        except:
            print("send_angles: failure to contact ESP32")
            self.aliensocket = None
            self.is_online = False
            return False

        return True

    def send_instructions(self, up:bool, down:bool, left:bool, right:bool, step_v:float, step_h:float) -> bool:
        if time() - self.last_sent > 0.2:
            self.last_sent = time()
        else:
            return True

        self.current_pos = self.get_angles()
        
        if self.current_pos is None:
            printf("Failure to get current angles!")
            return False
        
        target = self.current_pos

        if up:
            target = (self.current_pos[0], self.current_pos[1] - step_v)
        if down:
            target = (self.current_pos[0], self.current_pos[1] + step_v)
        if left:
            target = (self.current_pos[0] - step_h, self.current_pos[1])
        if right:
            target = (self.current_pos[0] + step_h, self.current_pos[1])
        
        # Limits
        if target[0] < self.limits[0][0]:
            target = (self.limits[0][0], target[1])
        if target[1] > self.limits[0][1]:
            target = (self.limits[0][1], target[1])
        
        if target[1] < self.limits[1][0]:
            target = (target[0] , self.limits[1][0])
        if target[1] > self.limits[1][1]:
            target = (target[0] , self.limits[1][1])

        return self.send_angles(target)