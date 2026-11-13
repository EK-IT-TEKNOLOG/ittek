# An "Educaboard roamer" program using most of the H/W
from machine import ADC, Pin
from time import sleep

from gpio_lcd import GpioLcd                # LCD

from machine import UART                    # GPS program
from gps_simple import GPS_SIMPLE

import funkyFunctions

###########################################################
# CONFIGURATION
local_offset_hours  = 1
local_offset_minuts = 0
daylight_saving     = False

adc2mV = 2050.0 / 4095.0               # LMT84 and ADC calibration
# V = (-5.50 mV/°C) T + 1035 mV        # LMT84 datasheet formula
# T = (V - 1035 mV) / (-5.5 mV/°C)
alpha = -5.5
beta = const(1035)

#########################################################################
# OBJECTS
lcd = GpioLcd(rs_pin = Pin(27), enable_pin = Pin(25),   # Create the LCD object
              d4_pin = Pin(33), d5_pin = Pin(32), d6_pin = Pin(21), d7_pin = Pin(22),
              num_lines = 4, num_columns = 20)

uart = UART(2, 9600)                   # UART object creation
gps = GPS_SIMPLE(uart, False)          # GPS object creation

adcLmt84 = ADC(Pin(35))                # LMT84 temperature        
adcLmt84.atten(ADC.ATTN_6DB)

###########################################################
# VARIABLES
old_day = -1

###########################################################
# FUNCTIONS
def ctrlC():
    try:
        pass
    except KeyboardInterrupt:
        print("Ctrl+C pressed - exiting program.")
        sys.exit()   

###########################################################
# PROGRAM
# Splash screen
print("Educaboard ESP32 roamer\n")

lcd.putstr("* Educaboard ESP32 *")

lcd.move_to(1, 1)
lcd.putstr("KEA ITT www.kea.dk")

lcd.move_to(1, 2)
lcd.putstr(" Bo Hansen, E442")

lcd.move_to(6, 3)
lcd.putstr("Roamer ")

happy_face = bytearray([0x00, 0x0A, 0x00, 0x04, 0x00, 0x11, 0x0E, 0x00])
lcd.custom_char(0, happy_face)
lcd.putchar(chr(0))

sleep(2)

# Preformat LCD
lcd.clear()
lcd.move_to(0, 1)
lcd.putstr("La:")
lcd.move_to(0, 2)
lcd.putstr("Lo:")
lcd.move_to(14, 2)
lcd.putstr("A:")
lcd.move_to(0, 3)
lcd.putstr("Q:  S:   H:    T:")


while True:
    if (gps.receive_nmea_data()):
        if (old_day != gps.get_utc_day()):  # Only update if there is a new day. LCDs are slow so only write if necessary
            lcd.move_to(0, 0)
            lcd.putstr(f"{gps.get_utc_year():04}-{gps.get_utc_month():02}-{gps.get_utc_day():02}")
            old_day = gps.get_utc_day()
        
        lcd.move_to(12, 0)
        lcd.putstr(f"{gps.get_utc_hours():02}:{gps.get_utc_minutes():02}:{gps.get_utc_seconds():02}")

        local_time = funkyFunctions.utc_to_local(gps.get_utc_year(), gps.get_utc_month(), gps.get_utc_day(), gps.get_utc_hours(), gps.get_utc_minutes(), gps.get_utc_seconds(), local_offset_hours, local_offset_minuts, daylight_saving)
        lcd.move_to(15, 1)
        lcd.putstr(f"{local_time[3]:02}:{local_time[4]:02}")

        lcd.move_to(3, 1)
        lcd.putstr(f"{gps.get_latitude():9.4}")
        lcd.move_to(3, 2)
        lcd.putstr(f"{gps.get_longitude():9.4}")

        lcd.move_to(16, 2)
        lcd.putstr(f"{round(gps.get_altitude()):4}")

        lcd.move_to(2, 3)
        lcd.putstr(f"{gps.get_fix_quality()}")
        lcd.move_to(6, 3)
        lcd.putstr(f"{gps.get_satellites():2}")
        lcd.move_to(11, 3)
        if (gps.get_hdop() > 9.9):
            lcd.putstr(f"{round(gps.get_hdop()):3}")
        else:
            lcd.putstr(f"{gps.get_hdop():3.1}")
    else:
        adcVal = 0
        
        for i in range (64):
            adcVal += adcLmt84.read()
        adcVal = adcVal / 64

        temp = (adc2mV *  adcVal - beta) / alpha
        lcd.move_to(17, 3)
        lcd.putstr(f"{round(temp):3}")
        
        
    ctrlC()