from machine import Pin,PWM
import time
import asyncio, socket
import random
import neopixel
from Servo import Servo

H_SERVO_PIN = 5
V_SERVO_PIN = 4

H_MIN = 90
H_MAX = 180
V_MIN = 105
V_MAX = 170

H_START_ANGLE = (H_MIN + H_MAX) / 2
V_START_ANGLE = (V_MIN + V_MAX) / 2

test_mov = True
target_coord = (H_START_ANGLE, V_START_ANGLE)
motor_h=Servo(pin=H_SERVO_PIN)
motor_v=Servo(pin=V_SERVO_PIN)
shutdown_event = asyncio.Event()
force_off = False
laser = Pin(3, Pin.OUT)

async def blink():
    np = neopixel.NeoPixel(Pin(7), 1)
    while True:
        np[0] = (0, 64, 0)
        np.write()
        await asyncio.sleep_ms(1000)
        np[0] = (0, 0, 0)
        np.write()
        await asyncio.sleep_ms(1000)

@micropython.native
async def blink_laser():
    global force_off, laser
    blink = True
    while True:
        if force_off:
            laser.value(True)
        else:
            laser.value(blink)
        blink = not blink
        await asyncio.sleep_ms(100)
        
async def handle_client(reader, writer):
    global target_coord, test_mov, force_off, laser
    request = None
    while request != 'quit':
        try:
            request = (await reader.read(255)).decode('utf8')
        except:
            await asyncio.sleep(0.1)
            continue
        print(f"Received={request}")
        response = "?\n"
        if request.startswith("("):
            try:
                target_coord = eval(request)
                response = "1"
            except:
                response = "0"
            
        if request == "test":
            test_mov = True
            response = "1"
        if request == "stop":
            test_mov = False
            response = "1"
        if request == "off":
            force_off = True
            laser.value(True)
            response = "1"
        if request == "on":
            force_off = False
            laser.value(False)
            response = "1"
        writer.write(response.encode('utf8'))
        await writer.drain()
    writer.close()


async def run_server():    
    server = await asyncio.start_server(handle_client, '192.168.2.55', 15555)
    print('Server started')
    async with server:
        await shutdown_event.wait()
    print('leaving run_server')

async def stop_servo():
    global motor_h, motor_v
    motor_v.move(V_START_ANGLE)
    motor_h.move(H_START_ANGLE)
    await asyncio.sleep(0.5)
    print(f"Stop servo (H,V)={H_START_ANGLE},{V_START_ANGLE}")

async def test_movement():
    global test_mov
    global motor_h, motor_v
    h = H_START_ANGLE
    v = V_START_ANGLE
    motor_v.move(H_START_ANGLE)
    motor_h.move(V_START_ANGLE)
    await asyncio.sleep(2)
    delay = 0.05

    range_h = range(H_MIN, H_MAX + 1)
    range_v = range(V_MIN, V_MAX + 1)
    while True:
        if not test_mov:
            await asyncio.sleep_ms(100)
            continue
        
        for h in range_h:
            motor_h.move(h)
            await asyncio.sleep(delay)
            print(f"(H,V)={h},{v}")
        for v in range_v:
            motor_v.move(v)
            await asyncio.sleep(delay)
            print(f"(H,V)={h},{v}")        
        for h in reversed(range_h):
            motor_h.move(h)
            await asyncio.sleep(delay)
            print(f"(H,V)={h},{v}")
        for v in reversed(range_v):
            motor_v.move(v)
            await asyncio.sleep(delay)
            print(f"(H,V)={h},{v}")

async def run_tracking():
    global target_coord
    global motor_h, motor_v
    h = H_START_ANGLE
    v = V_START_ANGLE
    motor_v.move(H_START_ANGLE)
    motor_h.move(V_START_ANGLE)
    await asyncio.sleep(2)
    while True:
        if target_coord is not None:
            (h,v) = target_coord
            
            if h < H_MIN:
                h = H_MIN
            
            if h > H_MAX:
                h = H_MAX
            
            if v < V_MIN:
                v = V_MIN
            
            if v > V_MAX:
                v = V_MAX
                
            print(f"Target(H,V)={h},{v}")
            motor_h.move(h)
            motor_v.move(v)
            await asyncio.sleep_ms(50)
        target_coord = None
        await asyncio.sleep_ms(10)
        
async def main():
    asyncio.create_task(blink_laser())
    asyncio.create_task(blink())
    #asyncio.create_task(test_movement())
    asyncio.create_task(run_server())
    track = asyncio.create_task(run_tracking())
    await asyncio.sleep(1800)
    
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()  # Clear retained state
