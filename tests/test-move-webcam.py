# Manda coordinate da puntare a ESP32

import socket
import random
from time import sleep

aliensocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

aliensocket.connect(('192.168.1.220', 15555))

for i in range(100):  
    tuple = (random.randint(1,200), random.randint(1, 200))
    data = bytes(str(tuple), "utf-8")
    aliensocket.send(data)
    key = aliensocket.recv(1)

    truncKey = str(key)

    print(truncKey)
    sleep(1)

aliensocket.close()