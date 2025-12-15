# An Educaboard test program
import math, network, random, sys, uselect
from time import sleep, sleep_ms, ticks_diff, ticks_ms
from machine import ADC, I2C, Pin, PWM, SPI, UART
from neopixel import NeoPixel

# Third party libraries
from gpio_lcd import GpioLcd           # LCD

# Own libraries
from gps_simple import GPS_SIMPLE
from eeprom_24xx64 import EEPROM_24xx64
from portExp_MCP23S08 import PortExp_MCP23S08
from lmt87 import LMT87

########################################
# CONFIGURATION
pin_led1 = 26                          # LED1 pin
pin_np = pin_led1                      # LED1 and NeoPixel share the same pin
number_neopixels = 2                   # The number of NeoPixel LEDs

pin_potmeter = 34                      # The potmeter pin

pin_lcd_contrast = 23                  # The LCD PWM contrast pin
contrast_level = 250                   # Varies from LCD to LCD and wanted contrast level: 0-1023

pin_pps = 5                            # The GPS PPS pin

pin_pb1 = 4                            # The push button 1 pin
pin_pb2 = 0                            # The push button 2 pin

pin_temperature = 35                   # The LMT87 temperature ssensor pin

# Rotary encoder pins, actual A or B depends the rotary encoder hardware. If backwards swap the pin numbers
pin_enc_a = 36
pin_enc_b = 39

# PORT EXPANDER
pin_portexp_cs = 15                    # The MCP23S08 CS pin number
pin_portexp_int = 2                    # The MCP23S08 interrupt pin on the ESP32
gp_t1 = 0                              # T1 NPN base
gp_t2 = 1                              # T2 PNP base
gp_led2 = 2                            # LED2: active low
gp_led3 = 3                            # LED3: active high
gp_repb = 4                            # Rotary encoder push button
gp_lcd_backlight = 5                   # LCD backlight control
gp_buzzer = 6                          # Buzzer

led23_on_off_time = 500                # The LED2 and LED3 toggle on/off time in ms

########################################
# OBJECTS
usb = uselect.poll()                   # Set up an input polling object.
usb.register(sys.stdin, uselect.POLLIN)# Register polling object.

led1 = Pin(pin_led1, Pin.OUT)          # The red LED, LED1
np = NeoPixel(Pin(pin_np), number_neopixels) # The NeoPixel object

pb1 = Pin(pin_pb1, Pin.IN)             # External pull-up and debounce
pb2 = Pin(pin_pb2, Pin.IN)             # Direct connection with pull-up thus inverted

# Potmeter and ADC
potmeter_adc = ADC(Pin(pin_potmeter))  # The potmeter object
potmeter_adc.width(ADC.WIDTH_12BIT)    # 12 bits, must be the same resolution as the LMT87 which is 12 bits
potmeter_adc.atten(ADC.ATTN_11DB)      # Full range: 3,3 V

# Rotary encoder
rotenc_a = Pin(pin_enc_a, Pin.IN, Pin.PULL_UP)
rotenc_B = Pin(pin_enc_b, Pin.IN, Pin.PULL_UP)

# LCD
lcd = GpioLcd(rs_pin = Pin(27), enable_pin = Pin(25),   # Create the LCD object
              d4_pin = Pin(33), d5_pin = Pin(32), d6_pin = Pin(21), d7_pin = Pin(22),
              num_lines = 4, num_columns = 20)

lcd_contrast = PWM(Pin(pin_lcd_contrast)) # Create PWM object from a pin

# GPS
uart = UART(2, 9600)                   # UART object creation
gps = GPS_SIMPLE(uart, False)          # GPS object creation
gps_pps = Pin(pin_pps, Pin.IN)         # The PPS pin object

# SPI BUS AND MCP23S08
hspi = SPI(1, 10000000)                # Create the SPI bus object running at 10 MHz
portexp_addr = 0                       # The MSP23S08 subaddress, not a real SPI thing!
portExp = PortExp_MCP23S08(hspi, pin_portexp_cs, portexp_addr)

# EEPROM
i2c = I2C(0)                           # I2C H/W 0 object
eeprom = EEPROM_24xx64(i2c, 0x50)      # The EEPROM object

# TEMPERATURE
temperature = LMT87(pin_temperature)   # The temperature object

########################################
# EEPROM MAP
EEPROM_DEFAULTS_SET = const(7000)      # Default values set, 1 byte
EEPROM_DEFAULTS_SET_VALUE = 1
EEPROM_HW_VERSION = const(7001)        # The H/W version, 1 byte
EEPROM_HW_VERSION_VALUE = 2

EEPROM_USER_NAME = const(7002)         # The user name (handle), 20 + 1 bytes
# 7022 next available address

EEPROM_TEMP_SENSOR_T1 = const(7032)    # Temperature point 1, float 4 bytes
EEPROM_TEMP_SENSOR_ADC1 = const(7036)  # ADC point 1, word 2 bytes
EEPROM_TEMP_SENSOR_T2 = const(7038)    # Temperature point 2, float 4 bytes
EEPROM_TEMP_SENSOR_ADC2 = const(7042)  # ADC point 2, word 2 bytes
# 7034 next available address

EEPROM_MAC_ADDR_00 = const(7064)       # MAC adresse0, 6 bytes, 18 x 6 bytes = 108 bytes
# 7172 next available address

# Raspberry Pi adapter
EEPROM_ADC1_I2C_ADDRESS = const(8000)  # The potentiometer MCP3021 ADC I2C address
EEPROM_ADC2_I2C_ADDRESS = const(8001)  # The temperature sensor MCP3021 ADC I2C address

# EEPROM max address
EEPROM_MAX_ADDRESS = 8191

########################################
# VARIABLES
prev_pps = -1

prev_pot_val = -1
prev_red = -999
prev_green = -999

prev_pb1 = -1
prev_pb2 = -1

enc_state = 0                          # Rotary encoder state control variable
CW = 1                                 # Constant clock wise rotation
CCW = -1                               # Constant counter clock wise rotation
re_counter = 0                         # A counter that is incremented/decremented vs rotation

prev_led23_toggle_time = 0             # Non blocking flow control of LED2 and LED3 via SPI

prev_repb_val = False
repb_pressed = False                   # Controlled by the port expander interrupt when RE PB pressed

prev_buzzer_time = 0

prev_temp_time = 0

########################################
# FUNCTIONS
def ctrlC():
    try:
        pass
    except KeyboardInterrupt:
        print("Ctrl+C pressed - exiting program.")
        sys.exit()
        

def rainbow_gradient(value, max_value = 255):
    pi_2 = math.pi / 2.0
    angle = 1.25 * math.pi * value / max_value
    
    # Red
    if angle < pi_2:
        red = int(max_value * math.cos(angle))
        if red > max_value:
            red = max_value    
    elif angle > math.pi:
        red = -int(max_value * math.sin(angle))
        if red > max_value:
            red = max_value    
    else:
        red = 0

    # Green
    if angle < math.pi:
        green = int(max_value * math.sin(angle))
        if green > max_value:
            green = max_value
    else:
        green = 0
    
    # Blue
    if angle < pi_2:
        blue = 0
    else:
        blue = -int(max_value * math.cos(angle))
        if blue > max_value:
            blue = max_value
        
    return (red, green, blue)        
   

# Rotary encoder. Truth tables: Which one to use depends the actual rotary encoder hardware
def re_half_step():
    global enc_state
    
    encTableHalfStep = [
        [0x03, 0x02, 0x01, 0x00],
        [0x23, 0x00, 0x01, 0x00],
        [0x13, 0x02, 0x00, 0x00],
        [0x03, 0x05, 0x04, 0x00],
        [0x03, 0x03, 0x04, 0x10],
        [0x03, 0x05, 0x03, 0x20]]    
    
    enc_state = encTableHalfStep[enc_state & 0x0F][(rotenc_B.value() << 1) | rotenc_a.value()]
 
    # -1: Left/CCW, 0: No rotation, 1: Right/CW
    result = enc_state & 0x30
    if (result == 0x10):
        return CW
    elif (result == 0x20):
        return CCW
    else:
        return 0


def re_full_step():
    global enc_state

    encTableFullStep = [
        [0x00, 0x02, 0x04, 0x00],
        [0x03, 0x00, 0x01, 0x10],
        [0x03, 0x02, 0x00, 0x00],
        [0x03, 0x02, 0x01, 0x00],
        [0x06, 0x00, 0x04, 0x00],
        [0x06, 0x05, 0x00, 0x20],
        [0x06, 0x05, 0x04, 0x00]]

    enc_state = encTableFullStep[enc_state & 0x0F][(rotenc_B.value() << 1) | rotenc_a.value()]
 
    # -1: Left/CCW, 0: No rotation, 1: Right/CW
    result = enc_state & 0x30
    if (result == 0x10):
        return CW
    elif (result == 0x20):
        return CCW
    else:
        return 0
    
# The port expander interrupt handler
def portExp_interrupt(pin):
    global repb_pressed
    res = portExp.read_register(portExp.INTF)
    if res & 0x10:                                     # Find GP4
        repb_val = portExp.gp_get_value(gp_repb)       # Read the status of the RE PB
        portExp.gp_set_value(gp_lcd_backlight, repb_val) # Control the LCD backlight FET
        
        if (repb_val == 0):
            repb_pressed = True
        else:
            repb_pressed = False


# EEPROM check and write defaults values
def eeprom_check_and_defaults():
    # Check if the communication with the EEPROM is valid
    try:
        eeprom_val = eeprom.read_byte(EEPROM_MAX_ADDRESS)
        random_val = random.randint(0, 0xFF)
        if (eeprom_val == random_val):                     # If existing EEPROM value and random value is identical then XOR random value
            random_val = random_val ^ 0xFF
        eeprom.write_byte(EEPROM_MAX_ADDRESS, random_val)
        eeprom_val = eeprom.read_byte(EEPROM_MAX_ADDRESS)  # Read back the written value
        if (random_val != eeprom_val):
            return False

        # Default values set, 1 byte
        eeprom.write_byte(EEPROM_DEFAULTS_SET, EEPROM_DEFAULTS_SET_VALUE)

        # The H/W version, 1 byte
        eeprom.write_byte(EEPROM_HW_VERSION, EEPROM_HW_VERSION_VALUE)

        # The temperature sensor
        eeprom.write_float(EEPROM_TEMP_SENSOR_T1, 25.2)
        eeprom.write_word(EEPROM_TEMP_SENSOR_ADC1, 2659)
        eeprom.write_float(EEPROM_TEMP_SENSOR_T2, 24.2)
        eeprom.write_word(EEPROM_TEMP_SENSOR_ADC2, 2697)

        # Raspberry Pi adapter ADCs
        eeprom.write_byte(EEPROM_ADC1_I2C_ADDRESS, 0x48)   # These depends on the actual MCP3021s used!
        eeprom.write_byte(EEPROM_ADC1_I2C_ADDRESS, 0x4B)
        
        return True

    except:
        return False


# Wifi activation
def wifi(name):
    global lcd
    lcd.move_to(19, 2)                 # Position on the LCD for Wifi status
    
    try:
        ap = network.WLAN(network.AP_IF) # create access-point interface
        ap.config(ssid = name)         # Set the SSID of the access point
        ap.config(max_clients = 1)     # Set how many clients can connect to the network
        ap.config(channel = 9)         # Set the Wifi channel
        #ap.config(txpower = 2)         # Power levels [dBm]: 2, 5, 7, 8, 11, 13, 14, 15, 16, 18, 20 (default)
        ap.active(True)                # Activate the interface
        
        print("\nWifi på 2,4 GHz aktiveret med SSID: " + name)
        lcd.putstr('+')
    except:
        print("\nFejl ved aktivering af Wifi")
        lcd.putstr('-')

########################################
# PROGRAM
print("Educaboard Testprogram")
print("----------------------")
print("Drej på R7 (blå over displayet) indtil der er synlig tekst i displayet,")
print("og husk at JP5 bøjle/jumper skal sidde til højre og JP13 til venstre.")
print()

# Splash screen on the LCD
lcd.putstr('* Educaboard ESP32 *')
lcd.move_to(0, 1)
lcd.putstr('  EK ITEK www.ek.dk')
lcd.move_to(0, 2)
lcd.putstr('Indlejrede Systemer')
lcd.move_to(0, 3)
lcd.putstr('og Programmering   ')
happy_face = bytearray([0x00, 0x0A, 0x00, 0x04, 0x00, 0x11, 0x0E, 0x00])
lcd.custom_char(0, happy_face)
lcd.move_to(17, 3)
lcd.putchar(chr(0))
for i in reversed(range(3)):
    lcd.move_to(19, 3)
    lcd.putstr(str(i + 1))
    sleep(1)

lcd_contrast.freq(440)                      # Set PWM frequency on JP5
lcd_contrast.duty(contrast_level)

# Preformat LCD
lcd.clear()                                 # Clear the splash screen
lcd.putstr("HH:MM:SS iv")
lcd.move_to(0, 1)
lcd.putstr("P:  0   T:    R:   0")
lcd.move_to(0, 2)
lcd.putstr("E:     B:        W:")

# CONFIG PORT EXPANDER
portExp.write_register(portExp.IODIR, 0x10) # Bulk setting of GP7:5, GP4 as input and GP3:0 as output, datasheet 1.6.1
portExp.gp_pullup(gp_repb, portExp.ON)      # Enable pull-up on GP4 = RE PB, datasheet 1.6.7
portExp.gp_interrupt(gp_repb, portExp.ON)   # Enable interrupt on GP4, datasheet 1.6.3
portExp.gp_set_value(gp_lcd_backlight, portExp.ON)# Turn LCD FET on even if not used, JP13

# Prepare the interrupt handling from the port expander
portExp_interrupt_detect = Pin(pin_portexp_int, Pin.IN, Pin.PULL_UP)
portExp_interrupt_detect.irq(trigger = Pin.IRQ_FALLING, handler = portExp_interrupt)


# EEPROM check and write default values
lcd.move_to(2, 2)
if (eeprom_check_and_defaults() == False):
    lcd.putstr("not")
else:
    lcd.putstr(" OK")
    
    # Check if the name has been set, if not ask for it
    eeprom_name_length = eeprom.read_byte(EEPROM_USER_NAME)    # The user name (handle), 20 + 1 bytes. post 0 = string length
    if (eeprom_name_length <= 20):
        user_name = eeprom.read_string(EEPROM_USER_NAME)
        print("Hej %s, gå nu i gang med at teste dit Educaboard.\nHvis du vil ændre navn så indtast et nyt, maks 20 tegn." % user_name)
        lcd.move_to(0, 3)
        lcd.putstr(user_name)
        
        wifi(user_name)
    else:
        print("Indtast dit navn/kaldenavn på linien herunder, maks 20 tegn.")


gps.clear_frames_received()            # Clear the frames received flag just in case of currupted frames during start


while True:
    # GPS
    if (gps.receive_nmea_data()):
        lcd.move_to(0, 0)
        lcd.putstr("%02d:%02d:%02d" % (gps.get_utc_hours(), gps.get_utc_minutes(), gps.get_utc_seconds()))

        lcd.move_to(9, 0)
        if (gps.get_validity() == "A"):
            lcd.putstr("va")
        else:
            lcd.putstr("iv")
        
        frames = gps.get_frames_received()
        if (frames & 0x0001 == 0x0001):
            lcd.move_to(16, 0)
            lcd.putstr("G")
        if (frames & 0x0002 == 0x0002):
            lcd.move_to(17, 0)
            lcd.putstr("R")
        if (frames & 0x0004 == 0x0004):
            lcd.move_to(18, 0)
            lcd.putstr("Z")
        if (frames & 0xFFF8 > 0):
            lcd.move_to(19, 0)
            lcd.putstr("!")
    
    pps = gps_pps.value()
    if (pps != prev_pps):
        lcd.move_to(12, 0)
        if (pps == 0):
            lcd.putstr("   ")
        else:
            lcd.putstr("PPS")
        prev_pps = pps
    
    
    # Potmeter
    pot_val = potmeter_adc.read() >> 4          # The potmeter returns a 12 bit value so normalize to 8 bits

    if (pot_val != prev_pot_val):
        lcd.move_to(3, 1)
        lcd.putstr("%3d" % pot_val)
        prev_pot_val = pot_val
        
    
    # LED1 linked to potmeter
    if (pot_val < 5):
        led1.on()
    else:
        led1.off()

    
    # NeoPixel linked to potmeter
    red, green, blue = rainbow_gradient(pot_val) 
    if prev_red != red or prev_green != green:
        
        # Fill each NeoPixels with the same RGB value
        for i in range(number_neopixels):
            np[i] = (red >> 2, green >> 2, blue >> 2)  # >> 2 reduce intensity, does impacthe smoothness of the gradient a bit
        
        np.write()
        
        prev_red = red
        prev_green = green
        
    
    # Push buttons
    pb1_val = pb1.value()
    if (pb1_val != prev_pb1):
        lcd.move_to(10, 2)
        if (pb1_val == 0):
            lcd.putchar("1")
        else:
            lcd.putchar(" ")
        prev_pb1 = pb1_val
        
    pb2_val = pb2.value()
    if (pb2_val != prev_pb2):
        lcd.move_to(12, 2)
        if (pb2_val == 0):
            lcd.putchar("2")
        else:
            lcd.putchar(" ")
        prev_pb2 = pb2_val


    # Rotary encoder
    res = re_full_step()               # or: re_half_step()
    if (res == CW):
        if (re_counter < 99):
            re_counter += res
            lcd.move_to(17, 1)
            lcd.putstr("%3d" % re_counter)
    elif (res == CCW):
        if (re_counter > -99):
            re_counter += res
            lcd.move_to(17, 1)
            lcd.putstr("%3d" % re_counter)

    if (prev_repb_val != repb_pressed):  # RE PB
        lcd.move_to(14, 2)
        if (repb_pressed == True):
            lcd.putstr("RE")
        else:
            lcd.putstr("  ")
        prev_repb_val = repb_pressed
        
    
    # LMT87 temperature sensor
    if (ticks_diff(ticks_ms(), prev_temp_time) > 5000):  # Measure the tmperature every 5 s. ADC processing is slow so throttle back
        temp = temperature.get_temperature()
        lcd.move_to(10, 1)
        lcd.putstr("%3d" % temp)
        prev_temp_time = ticks_ms()
    
    
    # SPI and port expander
    if (ticks_diff(ticks_ms(), prev_led23_toggle_time) > led23_on_off_time):
        res = portExp.gp_get_value(gp_led2)
        if res == portExp.OFF:
            portExp.gp_set_value(gp_t1, portExp.ON)
            portExp.gp_set_value(gp_t2, portExp.ON)    # active low
            
            portExp.gp_set_value(gp_led2, portExp.ON)
            portExp.gp_set_value(gp_led3, portExp.ON)  # active low
        else:
            portExp.gp_set_value(gp_t1, portExp.OFF)
            portExp.gp_set_value(gp_t2, portExp.OFF)   # active low
            
            portExp.gp_set_value(gp_led2, portExp.OFF)
            portExp.gp_set_value(gp_led3, portExp.OFF) # active low
        
        prev_led23_toggle_time = ticks_ms()

    
    # Receive data from the USB
    if usb.poll(0):
        user_name = sys.stdin.readline()# Read one character at a time
        sys.stdin.readline()           # WEIRD! - Needed to avoid a second handling of the same input
        user_name = user_name.strip()  # Remove leading and trailing white spaces and control characters from the received string

        if (len(user_name) > 0) and (len(user_name) <= 20):
            eeprom.write_string(EEPROM_USER_NAME, user_name)
            lcd.move_to(0, 3)
            lcd.putstr(user_name)
            for i in range(20 - len(user_name)):   # Clear to end of the line in case there was a longer name
                lcd.putchar(' ')
            
            print("Hej %s, gå nu i gang med at teste dit Educaboard" % user_name)
            
            wifi(user_name)            # Activate the Wifi
        else:
            print("Ugyldigt navn/kaldenavn, prøv igen")

    
    # Buzzer, only active when the LCD backlight is off. Make sound around 500 Hz
    if (repb_pressed == True):
        ''' Non-blocking but very weak sound
        t = ticks_ms()
        if (ticks_diff(t, prev_buzzer_time) > 1):
            portExp.gp_set_value(7, t & 1)
            prev_buzzer_time = t
        '''
        
        portExp.gp_set_value(gp_buzzer, portExp.ON)
        sleep_ms(1)
        portExp.gp_set_value(gp_buzzer, portExp.OFF)
        sleep_ms(1)


    ctrlC()
