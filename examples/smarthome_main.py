# Smart Home program. Reads local devices and external sensors and controls external devices
# Hardware platform is an Educaboard
# MicroPython and ESP32 https://docs.micropython.org/en/latest/esp32/quickref.html
#
import sys, uselect                    # Needed for USB port use
from machine import ADC, I2C, Pin, PWM, SPI, UART
import math, time

########################################
# OWN MODULES
# Generic libraries not specific to this program
from eeprom_24xx64 import EEPROM_24xx64
from portExp_MCP23S08 import PortExp_MCP23S08
from gps_simple import GPS_SIMPLE
from mac_addr_tools import MAC_Tools as mt

# Modules specific to this program 
import smarthome_espnow as en
import smarthome_lcd as lcd
import smarthome_misc as misc

########################################
# CONFIGURATION
splash_strings = [                     # Welcome splash screen text, 20 charcters wide on three lines
        "KEA IT Teknolog 2024",
        "Indlejrede Systemer ",
        "Smart Home Dashboard",
        "                    "]        # The fourth line will be replaced with the MAC address
        #01234567890123456789
SPLASH_DELAY = const(1)                # Splash screen delay on the LCD

MAX_NUMBER_RECEIVERS = const(5)        # The max number of receivers. Max is 18 since two are reserved (dynamic and broadcast address)

########################################
# EEPROM MAP
EEPROM_TEMP_1 = const(4096)            # Float, 4 bytes
EEPROM_TEMP_2 = const(4100)            # Float, 4 bytes
EEPROM_ADC_1 = const(4104)             # Word, 2 bytes
EEPROM_ADC_2 = const(4106)             # Word, 2 bytes
EEPROM_MAC_ADDR_START = const(4108)    # Six bytes per entry * MAX_NUMBER_RECEIVERS

EEPROM_SHOW_BROADCAST_MESSAGES = const(4300) # 1 byte
EEPROM_BROADCAST_INTERVAL = const(4301)# 1 byte

EEPROM_USER_NAME = const(8000)         # Educaboard test program uses this address for the name

########################################
# OBJECTS
# Push buttons
pb1 = Pin(4, Pin.IN)                   # External pull-up and debounce
pb2 = Pin(0, Pin.IN)                   # Direct connection with pull-up thus inverted

# LED1
led1 = Pin(26, Pin.OUT)                # Create the LED1 is the red LED, LED2 and LED3 via port expander

# LCD contrast
potmeter_adc = ADC(Pin(34))            # Create the ADC object
potmeter_adc.width(ADC.WIDTH_10BIT)    # Set the potmeter ADC to 10 bits to match the PWM width. THIS APPLIES TO ALL ADC USE HEREAFTER!
potmeter_adc.atten(ADC.ATTN_11DB)      # Full range: 3,3 V
lcd_contrast = PWM(Pin(23))            # Create the PWM object from a pin

# UART
uart = UART(2, 9600)                   # Create the UART object creation
# GPS
gps = GPS_SIMPLE(uart, False)          # Create the GPS object creation

# I2C bus
i2c = I2C(0)                           # Create the I2C H/W 0 object
# EEPROM
eeprom = EEPROM_24xx64(i2c, 0x50)      # Create the EEPROM object on I2C address 0x50

# SPI BUS
hspi = SPI(1, 10000000)                # Create the SPI bus object running on HSPI/1 at 10 Mb/s
# MCP23S08
pin_portexp_cs = 15                    # The MCP23S08 CS pin number
pin_portexp_int = 2                    # The MCP23S08 interrupt pin on the ESP32
port_exp_addr = 0                      # The MSP23S08 subaddress, not a real SPI thing!
port_exp = PortExp_MCP23S08(hspi, pin_portexp_cs, port_exp_addr)

# USB port
usb = uselect.poll()                   # Set up an input polling but non-blocking object
usb.register(sys.stdin, uselect.POLLIN)# Register polling object

########################################
# VARIABLES
mac_addr_receiver = []                 # The list holding the MAC addresses of the receivers

# Non blocking flow control broadcast
next_time_broadcast = 0

# Changeable through the command line interface, CLI. EEPROM values overrule the below values
show_broadcast_messages = 1            # Show received broadcast messages: 0: no show, 1: show

broadcast_interval = 60                # Auto broadcast interval in s, 0 = no broadcast

user_name = ""                         # The user name/handle

########################################
# FUNCTIONS
def ctrlC():
    try:
        pass
    except KeyboardInterrupt:
        print("Ctrl+C pressed - exiting program.")
        sys.exit()
        
        
def get_mac_addr_bstring(index):
    mac_addr_bstring = bytearray()
    for i in range(6):
        mac_addr_bstring.append(mac_addr_receiver[index][i])
    return mac_addr_bstring


def print_mac_addr_list():
    for i in range(MAX_NUMBER_RECEIVERS):
        print(f"Receiver MAC address {i:2} : ", end = "")
        if mt.cast_type_ba(mac_addr_receiver[i]) != "Unicast":           
            print("** unallocated **")
        else:
            for j in range(6):             # Each entry takes six bytes
                byte = mac_addr_receiver[i][j]
                if j < 5:
                    print(f"{byte:02X}:", end = "")
                else:
                    print(f"{byte:02X}")   # Print the last byte without the trailing colon


def write_defaults():
    # LMT84 calibration values
    misc.set_temp_calibration(0.0, 750, 21.5, 666) # Set the calibration values
    eeprom.write_float(EEPROM_TEMP_1, 0.0)# Save the calibration values to the EEPROM
    eeprom.write_word(EEPROM_ADC_1, 750)
    eeprom.write_float(EEPROM_TEMP_2, 21.5)
    eeprom.write_word(EEPROM_ADC_2, 666)
    
    # Show broadcast messages 
    show_broadcast_messages = 0# Show broadcast messages
    eeprom.write_byte(EEPROM_SHOW_BROADCAST_MESSAGES, show_broadcast_messages)
    
    # Broadcast interval in s
    broadcast_interval = 60    # Send every 60 s
    eeprom.write_byte(EEPROM_BROADCAST_INTERVAL, broadcast_interval)


def print_configuration():
    res = sys.implementation
    print(f"Name                    : {str(res[0])}")
    major, minor, patch, dummy = res[1]
    print(f"Version                 : {major}.{minor}.{patch}")
    print(f"Platform                : {str(res[2])}")
    print()
    print(f"User name               : {user_name}")
    print()
    print(f"Show broadcast messages : {show_broadcast_messages}")
    print(f"Broadcast interval [s]  : {broadcast_interval}")
    print()
    print(f"Dashboard MAC address   : {mt.bstr_to_str(misc.get_wifi_mac_address())}")
    print_mac_addr_list()
    print()


def usb_scan_and_parse(cmd_echo = True):
    global show_broadcast_messages 
    global broadcast_interval
    global user_name
    
    # Receive user input from the USB
    if usb.poll(0):                    # Check if there is any USB data available
        string = sys.stdin.readline()  # Read one line at a time
        sys.stdin.readline()           # WEIRD! - Needed to avoid a second handling of the same input
        string = string.strip()        # Remove leading and trailing white spaces and control characters from the received string
        if cmd_echo:
            print("Command: " + string)# Echo the USB string on the USB port
        
        # Print the dashboard's MAC address, rd mac addr
        if string == "rd mac addr":
            mac_addr = mt.bstr_to_str(misc.get_wifi_mac_address())
            print(mac_addr)            
        
        # List all the MAC addresses, rd mac list
        elif string == "rd mac list":
            print_mac_addr_list()
            
        # Clear the MAC address list, wr mac clear
        elif string == "wr mac clear":
            for i in range(6 * MAX_NUMBER_RECEIVERS): # Each entry takes six bytes and there are max 20 entries
                eeprom.write_byte(EEPROM_MAC_ADDR_START + i, 0xFF) # Clear the EEPROM entries
                mac_addr_receiver[int(i / 6)][i % 6] = 0xFF # Clear the list entries

        # Update a receiver's MAC address, wr mac add NUM ADDR 
        elif string[0:11] == "wr mac upd ":
            parts = string.split()
            if len(parts) == 5: # The command consists of exactly five part
                try:
                    number = int(parts[3])
                    mac_addr = str(parts[4])
                    
                    # Just a simple check of number and MAC address
                    if number >= 0 and number < MAX_NUMBER_RECEIVERS and len(mac_addr) == 17:
                        # Delete old entry from ESP-Now if any
                        existing_mac_addr_bstring = get_mac_addr_bstring(number)
                        if existing_mac_addr_bstring != en.MAC_ADDR_BROADCAST: # Make sure that the broadcast address is not deleted
                            en.esp_now_delete_mac_address(existing_mac_addr_bstring)
                        
                        # Update the MAC address entry in the EEPROM
                        mac_addr_parts = mac_addr.split(':')
                        
                        for i in range(6):
                            mac_addr_byte = int(mac_addr_parts[i], 16) # Convert each byte in hex notation to an int
                            if mac_addr_byte >= 0 and mac_addr_byte <= 0xFF:
                                eeprom.write_byte(EEPROM_MAC_ADDR_START + 6 * number + i, mac_addr_byte)# EEPROM: Each entry takes six bytes and there are max 20 entries
                            
                                mac_addr_receiver[number][i] = mac_addr_byte # MAC address list
                            else:
                                print("Invalid MAC address")
                                return    # No need to continue
                            
                        # Update ESP-NOW
                        mac_addr_bstring = get_mac_addr_bstring(number)
                        en.esp_now_add_mac_address(mac_addr_bstring)
                    else:
                        print("Invalid number and/or MAC address")
                except ValueError:
                   print("Invalid value(s)")             
            else:
                print("Invalid number of parameters")

        # Read the temperature ADC, rd temp adc
        elif string == "rd temp adc":
            adc_val = misc.get_temp_adc()
            print(adc_val)
            
        # Read the temperature, wr temp
        elif string == "rd temp":
            temp = misc.get_temperature()
            print(f"{temp:,.1}")

        # Write the temperature calibration values, wr temp cal T1 A1 T2 A2
        elif string[0:12] == "wr temp cal ":
            parts = string.split()
            if len(parts) == 7: # The command consists of exactly seven part
                try:
                    t1 = float(parts[3])
                    adc1 = int(parts[4])
                    t2 = float(parts[5])
                    adc2 = int(parts[6])
                    misc.set_temp_calibration(t1, adc1, t2, adc2)
                    
                    # Save the calibration values to the EEPROM
                    eeprom.write_float(EEPROM_TEMP_1, t1)
                    eeprom.write_word(EEPROM_ADC_1, adc1)
                    eeprom.write_float(EEPROM_TEMP_2, t2)
                    eeprom.write_word(EEPROM_ADC_2, adc2)
                except ValueError:
                   print("Invalid value(s)")                    
            else:
                print("Invalid number of parameters")
            
        # Broadcast a message, wr bc msg MESSAGE
        elif string[0:10] == "wr bc msg ":
            msg = string[10:]
            if len(msg) > 0 and len(msg) < 250: # Max 249 chars since the first is an *
                en.esp_now_send_message(en.MAC_ADDR_BROADCAST, '*' + msg)
            else:
                print("Message missing or to long")

        # Set the show broadcasts, wr bc show VALUE
        elif string[0:11] == "wr bc show ":
            parts = string.split()
            if len(parts) == 4: # The command consists of exactly four part
                try:
                    value = int(parts[3])
                    if value in (0, 1):
                        show_broadcast_messages = value
                        eeprom.write_byte(EEPROM_SHOW_BROADCAST_MESSAGES, show_broadcast_messages)
                    else:
                        print("Invalid value")
                except ValueError:
                   print("Invalid value")                    
            else:
                print("Invalid command")
                
        # Set the broadcast interval, wr bc int INTERVAL
        elif string[0:10] == "wr bc int ":
            parts = string.split()
            if len(parts) == 4: # The command consists of exactly four part
                try:
                    interval = int(parts[3])
                    if interval >= 0 and interval <= 255:
                        broadcast_interval = interval
                        eeprom.write_byte(EEPROM_BROADCAST_INTERVAL, broadcast_interval)
                    else:
                        print("Invalid value")
                except ValueError:
                   print("Invalid value")                    
            else:
                print("Invalid command")                

        # Send a mesage to a receiver with an index number, wr rx NUM MESSAGE or wr rx ADDR MESSAGE
        elif string[0:6] == "wr rx ":
            parts = string.split()
            if len(parts) >= 4: # The command consists of exactly four part, but the message could be with multiple spaces
                try:
                    # Find out if part[2] is a number or a MAC address
                    res = mac_addr_to_bstring(parts[2])  # Returns None if invalid MAC address
                    if res != None:                      # The result is a valid MAC address 
                        mac_addr_bstring = res           # The result was a valid MAC address so give it another name
                        pos_of_addr = string.find(parts[2]) # Find the start of the message by finding the location of the MAC address
                        msg = string[pos_of_addr + 18:] # Extract the message from the string, +18 because of the MAC address and the following space
                        msg = msg.strip()
                        if len(msg) > 0 and len(msg) <= 250:
                            if en.esp_now_mac_in_list(mac_addr_bstring): # Check if the MAC address is already in the list
                                en.esp_now_send_message(mac_addr_bstring, msg)
                            else:      # The MAC address is not in the list so add it, send the message and delete it
                                en.esp_now_add_mac_address(mac_addr_bstring)
                                en.esp_now_send_message(mac_addr_bstring, msg)
                                en.esp_now_delete_mac_address(mac_addr_bstring)
                        else:
                            print("Message to long")                    
                    else:              # parts[2] was not a valid MAC address so try to see if it is a valid integer
                        number = int(parts[2])
                        if number >= 0 and number < MAX_NUMBER_RECEIVERS:
                            pos_of_number = string.find(parts[2]) # Find the start of the message by finding the location of the number of receiver
                            msg = string[pos_of_number + 2:] # Extract the message from the string, +2 because of the number and the following space
                            if len(msg) > 0 and len(msg) <= 250:
                                mac_addr_bstring = get_mac_addr_bstring(number)  # Replace with receiver index
                                en.esp_now_send_message(mac_addr_bstring, msg)
                            else:
                                print("Message to long")
                        else:
                            print("Invalid receiver")
                except ValueError:
                   print("Invalid value(s)")                    
            else:
                print("Incomplete command")                

        # Set the user name, wr user NAME
        elif string[0:8] == "wr user ":
            parts = string.split()
            if len(parts) >= 3: # The command consists of exactly three part, but the name could be with multiple spaces
                try:
                    name = string[8:].strip() # Extract the name from the string
                    if len(name) > 0 and len(name) <= 20:
                        user_name = name
                        eeprom.write_string(EEPROM_USER_NAME, user_name)
                    else:
                        print("User name missing or to long")
                except ValueError:
                   print("Invalid name")                    
            else:
                print("Incomplete command")             
          
        # Read the configuration, rd cfg
        elif string == "rd cfg":
            print("\nConfiguration")
            print("-------------")
            print_configuration()
            
        # Configure the program to its defaults calues, wr defaults
        elif string == "wr defaults":
            write_defaults()

        # Print help text
        elif string == "help" or string == "?":
            print("\nAvailable commands")
            print("------------------")
            print("rd mac addr               to read this device\'s MAC address")
            print("wr mac clear              to clear the MAC address list")
            print("rd mac list               to list the MAC addresses of the receivers")
            print("wr mac upd NUM ADDR       to update receiver NUMber\'s MAC ADDRess")
            print()
            print("rd temp                   to read the on-board LMT84 temperature sensor")
            print("rd temp adc               to read the LMT84 ADC value at the present temperature")
            print("wr temp cal T1 A1 T2 A2   to write the LMT84 calibration values, where T# is the temp. and A# is the associated ADC value")
            print()
            print("wr bc int INTERVAL        to set the auto broadcast INTERVAL in seconds: 0: disabled, 1-255: enabled")
            print("wr bc msg MESSAGE         to send a broadcast with the MESSAGE")
            print("wr bc show VALUE          to enable/disable seeing broadcasts, 0: disabled, 1: enabled")
            print()
            print("wr rx ADDR MESSAGE        to send the MESSAGE to receiver with the MAC ADDRess")
            print("wr rx NUM MESSAGE         to send the MESSAGE to receiver NUMber in the MAC address list")
            print()
            print("wr user NAME              to set the user NAME or handle")
            print()
            print("rd cfg                    to read the current configuration")
            print("wr defaults               to set the program default values")
            print()
            print("Replace upper case words with relevant data\n")
        
        elif string[0:3] == "mt ":
            parts = string.split()
            print(misc.mac_addr_str_validate(parts[1]))
        
        else:                                
            print("Unknown command")   # Command not found so prompt the user

########################################
# PROGRAM

# INITIALIZATION
# Splash screen on USB and LCD
for i in range(3):
   print(splash_strings[i])            # Print on the USB port
bstr = misc.get_wifi_mac_address()
splash_strings[3] = " " + mt.bstr_to_str(bstr) # MAC address in fourth line, overwriting existing data if any
lcd.print_splash_screen(splash_strings)
print()

# EEPROM
# Check if the EEPROM is ready
try:
    eeprom.read_byte(0)
except:
    print("ERROR :: EEPROM error, the program has stopped :: ERROR")
    sys.exit("Error message")

# Check if the EEPROM values look "untuched", if so write the default values
if math.isnan(eeprom.read_float(EEPROM_TEMP_1)) == True or math.isnan(eeprom.read_float(EEPROM_TEMP_2)) == True:
    print("The Educaboard looks uncalibrated, so using default values")
    write_defaults()

# Load temperature coefficients and set the calibration
t1 = eeprom.read_float(EEPROM_TEMP_1)
adc1 = eeprom.read_word(EEPROM_ADC_1)
t2 = eeprom.read_float(EEPROM_TEMP_2)
adc2 = eeprom.read_word(EEPROM_ADC_2)
misc.set_temp_calibration(t1, adc1, t2, adc2)
print()

# Load the show broadcast messages
show_broadcast_messages = eeprom.read_byte(EEPROM_SHOW_BROADCAST_MESSAGES)
if show_broadcast_messages > 1:        # Only 0: no show, 1: show
    show_broadcast_messages = 1

# Load the broadcast interval
broadcast_interval = eeprom.read_byte(EEPROM_BROADCAST_INTERVAL)

# Load the user name
user_name = eeprom.read_string(EEPROM_USER_NAME)
if len(user_name) > 20:                # Trunc a user name longer than 20 chars
    user_name = user_name[0:20]
    eeprom.write_byte(EEPROM_USER_NAME, 20) # Also set it to max 20

# Load receivers' MAC addresses into list and print to dashboard
if MAX_NUMBER_RECEIVERS > 18:
    print("ERROR  Max number of receivers exceeded  ERROR")
    print("Reduce the MAX_NUMBER_RECEIVERS and run again.")
    print("The program has been stopped!")
    sys.exit("Error message")

for i in range(MAX_NUMBER_RECEIVERS):
    for j in range(6):
        mac_addr_receiver.append([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        mac_addr_receiver[i][j] = eeprom.read_byte(EEPROM_MAC_ADDR_START + 6 * i + j)

# Load ESP-Now with MAC-addresses
for i in range(MAX_NUMBER_RECEIVERS):
    mac_addr_bstring = get_mac_addr_bstring(i)  # Get a byte string with the MAC address
    if mac_addr_bstring != en.MAC_ADDR_BROADCAST: # Don't add broadcast MAC address (same as cleared list)
        en.esp_now_add_mac_address(mac_addr_bstring) # Add the MAC address to ESP-NOW
en.esp_now_add_mac_address(en.MAC_ADDR_BROADCAST)  # Always add broadcast address

# Initialize the port expander
port_exp.write_register(port_exp.IODIR, 0xF0) # Bulk setting of GP7:4 as input and GP3:0 as output, datasheet 1.6.1
port_exp.gp_pullup(5, port_exp.ON)     # Enable pull-up on GP5, datasheet 1.6.7
port_exp.gp_pullup(6, port_exp.ON)     # Enable pull-up on GP6, datasheet 1.6.7

# Initialization done, now ready for use
print_configuration()
print(f"\nHi {user_name}, time for some Smart Home fun?")
time.sleep(SPLASH_DELAY)
lcd.preformat_screen()
print("\nEnter   help   or   ?   for available commands\n")

# MAIN (super loop)
while True:
    # Check local devices
    pb1_val = pb1.value()              # Read onboard push button 1, active low
    pb2_val = pb2.value()              # Read onboard push button 2, active low
    pb3_val = port_exp.gp_get_value(5) # Read external push button via the port expander GP5, active low
    pb4_val = port_exp.gp_get_value(6) # Read external push button via the port expander GP6, active low
    
    temp = misc.get_temperature()      # Read the temperature from the LMT84
    
    pot_val = potmeter_adc.read()      # Read the potmeter and set the LCD contrast level
    lcd_contrast.duty(pot_val)
    
    gps_data_available = gps.receive_nmea_data()
    
    
    # *********************************************************************************************
    # Check ESP-NOW sensors
    tx_mac_addr, msg = en.esp_now_receive_message() # Check to see if there is a message and return it and the transmitter MAC address is any
    if msg:
        msg = msg.decode("utf-8")
        mac_addr = mt.bstr_to_str(tx_mac_addr)
        if msg[0] == '*':              # By design, KEA ITT, is the first char of a broadcast messages an *
            if show_broadcast_messages == 1: # Only show broadcast messages if wanted. Control in Configuration
                lcd.print_received_frame(mac_addr, msg)
                print("Broadcast " + mac_addr + "  " + msg[1:]) # Remove the broadcast identifier *
        else:
           lcd.print_received_frame(mac_addr, msg)
           print("Message   " + mac_addr + "  " + msg)
           parts = msg.split('|')
           # Do something with the direct messages here
           
    # *********************************************************************************************
 
    
    # Control local devices
    led1.value(not pb1_val)            # LED1 control is active high but PB1 is active low so invert
    port_exp.gp_set_value(2, pb2_val)  # GP2: LED2 control is active low and PB2 is also active low so no invert
    port_exp.gp_set_value(3, not pb3_val) # GP3: LED3 control is active high but PB3 is active low so invert
    port_exp.gp_set_value(0, not pb4_val) # GP0: external LED4 via T1 control is active low and PB4 is active low, but T1 inverts so invert
    
    # Print some GPS data and the temperature also on the LCD
    if gps_data_available == True:
        lcd.print_gps_data(gps.get_utc_year(), gps.get_utc_month(), gps.get_utc_day(),
                           gps.get_utc_hours(), gps.get_utc_minutes(), gps.get_utc_seconds(),
                           gps.get_fix_quality(), gps.get_satellites(), gps.get_hdop(), misc.get_temperature())
    
    # *********************************************************************************************
    # Control ESP-NOW devices
    # Send only if there is a change since last time!
    # mac_addr_bstring = get_mac_addr_bstring(0)  # Replace with receiver index 
    # en.esp_now_send_message(mac_addr_bstring, "The message")
    # *********************************************************************************************
    
    
    # Check USB port for commands
    usb_scan_and_parse()
    
    
    # Auto broadcast, if zero (0) then there is no auto broadcast
    if broadcast_interval > 0:
        if time.ticks_diff(time.ticks_ms(), next_time_broadcast) >= 0:
            en.esp_now_send_message(mt.MAC_ADDR_BROADCAST_BSTR, "*" + user_name + ": " + str(time.ticks_ms()))
            print("Broadcast " + user_name + ": " + str(time.ticks_ms()))
            next_time_broadcast = time.ticks_ms() + 1000 * broadcast_interval # Update the time for next time comparison

    
    # Check if Ctrl-C is pressed
    ctrlC()
