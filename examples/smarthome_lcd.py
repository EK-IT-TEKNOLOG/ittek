# Smart Home LCD handling functions module

#######################################
# IMPORTS
from machine import Pin
from time import sleep
import network

from gpio_lcd import GpioLcd           # LCD

#######################################
# OBJECTS
lcd = GpioLcd(rs_pin = Pin(27), enable_pin = Pin(25),   # Create the LCD object
              d4_pin = Pin(33), d5_pin = Pin(32), d6_pin = Pin(21), d7_pin = Pin(22),
              num_lines = 4, num_columns = 20)

#######################################
# VARIABLES
# Flow control
prev_bc_text = ""

prev_day = 0
prev_hours = 0
prev_minutes = 0
prev_seconds = 0
prev_quality = 0
prev_sats = 0
prev_hdop = 0
prev_temp = -999

#######################################
# FUNCTIONS

# Prints a splash screen on the display and USB port
def print_splash_screen(strings):
    for i in range(4):
        lcd.putstr(strings[i])         # Print on the display
        
# Preformat the LCD layout for real use, once the splash screen is done
def preformat_screen():
    lcd.clear()#01234567890123456789
    lcd.putstr("2024-01-01  00:00:00")
    lcd.move_to(0, 1)
    lcd.putstr("Q:0 S: 0 H:9.9 T:  0")
    

def print_received_frame(addr, string):
    global prev_bc_text
    
    # Format the frame message on the LCD
    lcd_text = addr[-5:]               # Get the last two bytes of the senders MAC address
    if string[0] != '*':
        lcd_text += ' '                # Insert a space if not a broadcast message
    lcd_text += string                 # Add the received message string
    lcd_text += "              "       # Fill the remainder with blanks, i.e. make sure teh rest of the line is cleared
    lcd_text = lcd_text[0:20]          # Only print a total of 20 characters
    
    # "Scroll" one line up
    lcd.move_to(0, 2)
    lcd.putstr(prev_bc_text)
    
    # Print new string
    lcd.move_to(0, 3)
    lcd.putstr(lcd_text)
    
    # Save the new string for the next time
    prev_bc_text = lcd_text
    
    
def print_gps_data(year, month, day, hours, minutes, seconds, quality, sats, hdop, temp):
    # Only update if there is a change. LCDs are slow so only write if necessary
    global prev_seconds
    global prev_minutes
    global prev_hours
    global prev_day
    global prev_quality
    global prev_sats
    global prev_hdop
    global prev_temp
 
    # Line 0
    if prev_seconds != seconds:
        lcd.move_to(18, 0)
        lcd.putstr(f"{seconds:02}")
        prev_seconds = seconds
    if prev_minutes != minutes:
        lcd.move_to(15, 0)
        lcd.putstr(f"{minutes:02}")
        prev_minutes = minutes
    if prev_hours != hours:
        lcd.move_to(12, 0)
        lcd.putstr(f"{hours:02}")
        prev_hours = hours

    if prev_day != day:                
        lcd.move_to(0, 0)
        lcd.putstr(f"{year:04}-{month:02}-{day:02}")
        prev_day = day

    # Line 1
    if prev_quality != quality:                
        lcd.move_to(2, 1)
        lcd.putstr(f"{quality:1}")
        prev_quality = quality

    if prev_sats != sats:                
        lcd.move_to(6, 1)
        lcd.putstr(f"{sats:2}")
        prev_sats = sats

    if prev_hdop != hdop:                
        lcd.move_to(11, 1)
        if hdop > 9.9:
            lcd.putstr(f"{round(hdop):3}")
        else:
            lcd.putstr(f"{hdop:3.1}")
        prev_hdop = hdop

    if prev_temp != temp:                
        lcd.move_to(17, 1)
        lcd.putstr(f"{round(temp):3}")
        prev_temp = temp
