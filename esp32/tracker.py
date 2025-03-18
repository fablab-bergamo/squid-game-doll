from machine import Pin, PWM
import time
import asyncio, socket
import random
import neopixel
from Servo import Servo

H_SERVO_PIN = 5
V_SERVO_PIN = 4
HEAD_SERVO_PIN = 3
EYES_PIN = 1
LASER_PIN = 2
INTEGRATED_RGB = 7

H_MIN = 0 + 30
H_MAX = 180 - 30  # H_MIN + 73
V_MIN = 0
V_MAX = 120
HEAD_MIN = 0
HEAD_MAX = 180

H_START_ANGLE = (H_MIN + H_MAX) / 2
V_START_ANGLE = (V_MIN + V_MAX) / 2
HEAD_START_ANGLE = HEAD_MIN

head_pos = HEAD_START_ANGLE
zero = (H_START_ANGLE, V_START_ANGLE)
test_mov = True
target_coord = (H_START_ANGLE, V_START_ANGLE)
motor_h = Servo(pin=H_SERVO_PIN)
motor_v = Servo(pin=V_SERVO_PIN)
motor_head = Servo(pin=HEAD_SERVO_PIN)
shutdown_event = asyncio.Event()
force_off = False

laser = Pin(LASER_PIN, Pin.OUT)
# Initialize PWM on the pin
eyes_pwm = PWM(Pin(EYES_PIN), freq=1000)


def set_brightness(duty):
    global eyes_pwm
    """Set the brightness of the LEDs using PWM duty cycle (0-1023)."""
    eyes_pwm.duty(duty)


async def rotate_head():
    """Asynchronous function to test head movement."""
    global motor_head
    print("Running rotate_head...")
    motor_head.move(0)
    await asyncio.sleep(5)
    while True:
        for angle in range(0, 181, 1):
            motor_head.move(angle)
            await asyncio.sleep_ms(20)
        await asyncio.sleep(1)

        for angle in range(180, 0, -1):
            motor_head.move(angle)
            await asyncio.sleep_ms(20)
        await asyncio.sleep(1)


async def pulse_eyes():
    """Asynchronous function to create a pulsing effect on the LEDs."""
    print("Running pulse_eyes...")
    step = 50
    while True:
        # Gradually increase brightness
        for duty in range(0, 1024, step):  # Steps of 10 for smooth effect
            set_brightness(duty)
            await asyncio.sleep(0.02)  # Small delay for smooth transition

        # Gradually decrease brightness
        for duty in range(1023, -1, -step):
            set_brightness(duty)
            await asyncio.sleep(0.02)


async def head_positionning():
    global head_pos, motor_head
    print("Running head_positionning...")
    while True:
        if int(motor_head.current_angle - head_pos) != 0:
            for angle in range(
                int(motor_head.current_angle), int(head_pos), 1 if head_pos > motor_head.current_angle else -1
            ):
                motor_head.move(angle)
        await asyncio.sleep(0.02)


async def blink():
    import network

    wlan = network.WLAN(network.STA_IF)

    np = neopixel.NeoPixel(Pin(INTEGRATED_RGB), 1)
    print("Running blink...")
    while True:
        if wlan.isconnected():
            np[0] = (0, 16, 0)
        else:
            np[0] = (16, 0, 0)
        np.write()
        await asyncio.sleep_ms(1000)
        np[0] = (0, 0, 0)
        np.write()
        await asyncio.sleep_ms(1000)


async def blink_laser():
    global force_off, laser
    print("Running blink laser...")
    blink = True
    while True:
        if force_off:
            laser.value(True)
        else:
            laser.value(blink)
        blink = not blink
        await asyncio.sleep_ms(100)


# possible commands


async def handle_client(reader, writer):
    """
    Handles client requests and sends appropriate responses.

    The function listens for various commands from the client and performs actions
    such as updating target coordinates, starting/stopping test movements, and
    controlling the laser. The possible commands and their responses are:

    - "(x, y)": Updates the target coordinates to (x, y). Responds with "1" if successful, "0" otherwise.
    - "?": Requests the current servo angles. Responds with a tuple of (horizontal_angle, vertical_angle).
    - "limits": Requests the servo limits. Responds with a tuple of ((H_MIN, H_MAX), (V_MIN, V_MAX)).
    - "test": Starts the test movement. Responds with "1".
    - "stop": Stops the test movement. Responds with "1".
    - "off": Forces the laser off. Responds with "1".
    - "on": Forces the laser on. Responds with "1".
    - "quit": Ends the client connection.

    Parameters:
    reader (StreamReader): The stream reader to read data from the client.
    writer (StreamWriter): The stream writer to send data to the client.
    """
    global target_coord, test_mov, force_off, laser, shutdown_event, head_pos
    request = None
    skipReply = False
    print("Handle client started")

    while request != "quit":
        try:
            request = (await asyncio.wait_for(reader.read(128), timeout=0.5)).decode("utf8").strip()
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f"Error reading request: {e}")
            await asyncio.sleep(0.1)

        if request is None or len(request) == 0:
            continue

        print(f"<-- {request}")
        response = "?\n"

        if request.startswith("("):
            try:
                target_coord = eval(request)
                response = "1"
            except Exception as e:
                print(f"Error updating target coordinates: {e}")
                response = "0"
        elif request == "angles":
            response = (round(motor_h.current_angle, 2), round(motor_v.current_angle, 2))
        elif request == "limits":
            response = ((H_MIN, H_MAX), (V_MIN, V_MAX))
        elif request == "test":
            test_mov = True
            response = "1"
        elif request == "stop":
            test_mov = False
            response = "1"
        elif request == "off":
            force_off = True
            laser.value(True)
            response = "1"
        elif request == "on":
            force_off = False
            laser.value(False)
            response = "1"
        elif request == "h0":
            head_pos = HEAD_MIN
            response = "1"
        elif request == "h1":
            head_pos = HEAD_MAX
            response = "1"
        elif request == "quit":
            response = "1"
        else:
            response = "0"

        print(f"--> {response}")
        try:
            writer.write(str(response).encode("utf8"))
            await writer.drain()
        except Exception as e:
            print(f"Error while responding: {e}")
            break

    writer.close()
    await writer.wait_closed()
    print("handle_client terminating.")
    shutdown_event.set()


async def run_server():
    print("Running server...")
    while True:
        shutdown_event.clear()
        server = await asyncio.start_server(handle_client, "0.0.0.0", 15555)
        print("Server started")
        async with server:
            await shutdown_event.wait()
        print("leaving run_server")


async def stop_servo():
    global motor_h, motor_v
    motor_h.move(zero[0])
    motor_v.move(zero[1])
    await asyncio.sleep(0.5)
    print(f"Stop servo, reset to (H,V)={zero}")


async def test_movement():
    global test_mov
    global motor_h, motor_v, zero

    print("Running test_movement...")
    h = zero[0]
    v = zero[1]

    motor_h.move(h)
    motor_v.move(v)

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

    print("Running run_tracking...")

    h = zero[0]
    v = zero[1]

    motor_h.move(h)
    motor_v.move(v)

    await asyncio.sleep(2)
    while True:
        try:
            if target_coord is not None:
                (h, v) = target_coord

                if h < H_MIN:
                    h = H_MIN

                if h > H_MAX:
                    h = H_MAX

                if v < V_MIN:
                    v = V_MIN

                if v > V_MAX:
                    v = V_MAX

                print(h, v)
                motor_h.move(h)
                motor_v.move(v)
                target_coord = None
                await asyncio.sleep_ms(100)
            else:
                v2 = v + random.uniform(-1.0, 1.0)
                h2 = h + random.uniform(-1.0, 1.0)
                print(h2, v2)
                motor_h.move(h2)
                motor_v.move(v2)
                await asyncio.sleep_ms(250)
        except Exception as e:
            print(f"Error:{e}")

    print("Run tracking terminating")


async def test(servo):
    print("Running test...")
    servo.move(90)
    await asyncio.sleep(1)
    servo.move(100)
    await asyncio.sleep(1)
    servo.move(110)
    await asyncio.sleep(1)


async def check_limits():
    global motor_h, motor_v
    print("Running check_limits...")
    motor_v.move(V_MIN)
    motor_h.move(H_MIN)
    DELAY_MS = 20
    while True:
        for i in range(H_MIN, H_MAX + 1):
            motor_h.move(i)
            await asyncio.sleep_ms(DELAY_MS)
        for i in range(V_MIN, V_MAX + 1):
            motor_v.move(i)
            await asyncio.sleep_ms(DELAY_MS)
        for i in range(H_MAX, H_MIN, -1):
            motor_h.move(i)
            await asyncio.sleep_ms(DELAY_MS)
        for i in range(V_MAX, V_MIN, -1):
            motor_v.move(i)
            await asyncio.sleep_ms(DELAY_MS)


async def main():
    # asyncio.create_task(blink_laser())
    asyncio.create_task(blink())
    # asyncio.create_task(test_movement())
    # asyncio.create_task(head_positionning())
    asyncio.create_task(pulse_eyes())
    asyncio.create_task(rotate_head())
    await test(motor_h)
    await test(motor_v)
    await asyncio.gather(run_server())  # , run_tracking())


try:
    asyncio.run(main())
except Exception as e:
    print(f"Error: {e}")
finally:
    asyncio.new_event_loop()  # Clear retained state
