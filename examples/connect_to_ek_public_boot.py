# -*- coding: utf-8 -*-
req = '''POST /index.php?zone=guest HTTP/1.1
Host: 192.168.200.1:8002
User-Agent: curl/8.21.0
Accept: */*
Content-Length: 12
Content-Type: application/x-www-form-urlencoded

accept=Login
'''

import gc
gc.collect()
import network
from machine import reset, Pin
from time import ticks_ms
# import requests
import urequests as requests
import socket

ssid = 'EK-PUBLIC'
password = ''

def do_connect():
    wlan = network.WLAN(network.STA_IF)
    print('WLAN status:', wlan.status())
    wlan.active(True)
    try:
        if not wlan.isconnected():
            print('connecting to network...')
            wlan.connect(ssid, password)
            print('WLAN status:', wlan.status())
            start = ticks_ms()
            while not wlan.isconnected():
                if ticks_ms() - start > 10000:
                    print("Could not connect to wifi!")
                    break

    except Exception as e:
        print(f"WiFi error '{e}' occured, rebooting system")
        reset()
    finally:
        if wlan.isconnected():
            print("Connected to wifi!")
            print(f"wifi statuscode {wlan.status()}")
    return wlan    
    
wlan = do_connect()
if wlan.isconnected():
    print('[+] Connected to WiFi', wlan.ifconfig())
    print('[+] Network test')
    addr_info = socket.getaddrinfo('192.168.200.1', 8002)
    addr = addr_info[0][-1]

    s = socket.socket()
    print('[+] Connecting to',addr)
    s.connect(addr)
    req_text = req.replace('\n','\r\n')
    s.send(req_text.encode('utf-8'))
    while True:
        data = s.recv(1024) # Adjust buffer size as needed
        if not data:
            break
        print(data.decode('utf-8'), end="")
    s.close()
    gc.collect()
    print('[+] Testing internet connection...')
    res = requests.get('https://www.dr.dk/')
    if res.status_code == 200:
        print('[+] Succesfully connected to the entaweb-machine')
    else:
        print('[-] Some error happend', res.status_code)
    gc.collect()
else:
    print('[-] Error connecting. Try again')
