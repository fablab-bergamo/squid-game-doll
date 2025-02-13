# This file is executed on every boot (including wake-boot from deepsleep)
import esp

def do_connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        wlan.active(True)
        wlan.config(txpower=8.5)
        print('connecting to network...')
        wlan.connect("SSID", "PASSWORD")
        print('connecting...')
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())
    
esp.osdebug(None)
do_connect()
#import webrepl
#webrepl.start()

import tracker

machine.freq(240_000_000)