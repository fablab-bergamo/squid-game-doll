# This file is executed on every boot (including wake-boot from deepsleep)
import esp
import time


def do_connect():
    import network

    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        wlan.active(True)
        wlan.config(txpower=8.0)
        print("connecting to network...")
        try:
            wlan.connect("SSID", "Password")
            wlan.config(dhcp_hostname="esp32tracker")
            print("connecting...")
            start = time.time()
            TIMEOUT = start + 10
            while not wlan.isconnected() and time.time() < TIMEOUT:
                pass
        except Exception as e:
            print("WiFi failed", e)
    print("network config:", wlan.ifconfig())


esp.osdebug(None)
import machine

print("🚀 ESP32 Tracker Boot Sequence")
print("=" * 40)

# Set CPU frequency for optimal performance
machine.freq(240_000_000)
print(f"⚡ CPU frequency set to: {machine.freq() / 1_000_000:.0f} MHz")

# Connect to WiFi
do_connect()

# Display hardware configuration before starting tracker
print("\n🔧 Hardware Configuration:")
print("-" * 25)

try:
    from constants import *
    print(f"📍 Pin Assignments:")
    print(f"   Head Servo:     GPIO {HEAD_SERVO_PIN}")
    print(f"   Eyes (PWM):     GPIO {EYES_PIN}")
    print(f"   Laser H-Servo:  GPIO {H_SERVO_PIN}")
    print(f"   Laser V-Servo:  GPIO {V_SERVO_PIN}")
    print(f"   Laser Module:   GPIO {LASER_PIN}")
    print(f"   Status RGB LED: GPIO {INTEGRATED_RGB}")

    print(f"\n⚙️  Servo Limits:")
    print(f"   Head Range:     {HEAD_MIN}° - {HEAD_MAX}°")
    print(f"   H-Axis Range:   {H_MIN}° - {H_MAX}°")
    print(f"   V-Axis Range:   {V_MIN}° - {V_MAX}°")

    print(f"\n🌐 Network Settings:")
    print(f"   Server Port:    {SERVER_PORT}")
    print(f"   Server Host:    {SERVER_HOST}")

except ImportError as e:
    print(f"⚠️  Could not load constants: {e}")

print("\n🎯 Starting Squid Game Doll Tracker...")
print("=" * 40)

import tracker
