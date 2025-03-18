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
            while not wlan.isconnected() and time.time() - TIMEOUT < 0:
                pass
        except Exception as e:
            print("WiFi failed", e)
    print("network config:", wlan.ifconfig())


esp.osdebug(None)
import machine

machine.freq(160_000_000)
do_connect()

import tracker
