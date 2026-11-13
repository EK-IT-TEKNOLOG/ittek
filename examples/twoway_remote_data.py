# A simple ESP32 <-> UART remote data system incl. EEPROM use
import sys, uselect
from machine import ADC, I2C, Pin, UART
from eeprom_24xx64 import EEPROM_24xx64
from gps_simple import GPS_SIMPLE

#########################################################################
# CONFIGURATION
# Remote
uart_remote_port = 1                   # Remote UART port
uart_remote_pin_tx = 33                # Remote UART TX pin
uart_remote_pin_rx = 32                # Remote UART RX pin
uart_remote_speed = 9600               # Remote UART speed, 8N1

# Battery
pin_adc_bat = 25                       # The battery status input pin
bat_scaling = 4.2 / <adc_4v2>          # The battery voltage scaling, replace <adc_4v2> with ADC value when 4,2 V is applied

# EEPROM map
eepmap_remote_bat_voltage = 1000       # The remote battery voltage address, float so 4 bytes
eepmap_remote_groupe_id = 1004         # The remote group ID address, 0-255 so 1 byte

# User data
group_id = 99                          # Own group ID, 0-255

# GPS
uart_gps_port = 2                      # GPS UART port
uart_gps_speed = 9600                  # GPS UART speed

#########################################################################
# OBJECTS
uart_remote = UART(uart_remote_port, baudrate = uart_remote_speed, tx = uart_remote_pin_tx, rx = uart_remote_pin_rx)# Remote UART object creation, 8N1

usb = uselect.poll()                   # Set up an input polling but non-blocking object
usb.register(sys.stdin, uselect.POLLIN)# Register polling object

i2c = I2C(0)                           # I2C H/W 0 object
eeprom = EEPROM_24xx64(i2c, 0x50)      # The EEPROM object

bat_adc = ADC(Pin(pin_adc_bat))        # The battery status ADC object
bat_adc.atten(ADC.ATTN_11DB)           # Full range: 3,3 V

uart_gps = UART(uart_gps_port, uart_gps_speed) # GPS UART object creation, 8N1
gps = GPS_SIMPLE(uart_gps)             # GPS object creation

#########################################################################
# FUNCTIONS

# Sends the input to the remote unit
#   Formats the input to be sent and adds <LF> terminator. UART can only send strings
#   Input : the header string
#           the data to be sent
#   Output: string formatted header=data to the UART
def send_response(header, data):
    data_to_string = str(data)         # Convert data to a string
    uart_remote.write(header + "=" + data_to_string + "\n") # Send it and add <LF> terminator

# Battery voltage function
#   Reads the battery from a converted ADC value
#   Input : none
#   Output: the battery voltage
def read_battery_voltage():
    adc_val = bat_adc.read()
    voltage = bat_scaling * adc_val
    return voltage

def read_battery_voltage_avg64():      # Option: average over 64 times to remove fluctuations
    adc_val = 0
    for i in range(64):
        adc_val += bat_adc.read()      
    voltage = bat_scaling * (adc_val >> 6) # >> is fast divide by 2^6 = 64
    return voltage

# Clibrates the voltage scaling
#   Reads ADC 64 times and then calculated the battery scaling factor
#   Before being called the battery (system) voltage must be 4,2 V
#   Input : none
#   Output: the battery voltage scaling
def calibrate_battery_scaling():
    print("Make sure that the battery voltage is 4.2 V, otherwise set and run again")
    adc_val = 0
    for i in range(64):
        adc_val += bat_adc.read()      
    bat_scaling = 4.2 / (adc_val >> 6) # >> is fast divide by 2^6 = 64
    
    print(f"Battery scaling is: {bat_scaling}")

#########################################################################
# PROGRAM

print("Two-way ESP32 remote data system\n")

while True:
    # Receive commands from and send responses to the remote UART
    if uart_remote.any() > 0:          # Check if there is any remote UART data available
        string = uart_remote.read().decode()  # UART returns bytes. They have to be conv. to chars/a string
        string = string.strip()        # Remove leading and trailing white spaces and control characters from received string
        print("Remote: " + string)     # Echo the received string on the USB port
        
        # Check if the received string is a valid command or response
        
        # Commands
        # rd bat
        if string == "rd bat":
            bat_voltage = read_battery_voltage() # Get the battery voltage
            send_response("batVoltage", bat_voltage) # Send the battery voltage to the remote unit
        
        # rd group
        elif string == "rd group":
            send_response("group", group_id) # Send the group ID
        
        # Reponses
        elif '=' in string:            # Check if a = is present in the received string, if so it is a response
            parts = string.split('=')  # Split response string into parts
            if len(parts) == 2:        # Check if there are exactly two parts in the response string
                header = parts[0]      # Copy the parts into more meaningful names    
                data = parts[1]

                # batVoltage=<float>
                if header == "batVoltage":
                    eeprom.write_float(eepmap_remote_bat_voltage, float(data))
                
                # groupId=<int>
                elif header == "groupId":
                    eeprom.write_byte(eepmap_remote_group_id, int(data))
                   
                # Unknown response received
                else:
                    print("Unknown response from the remote unit")
            
            # Invalid command/response received
            else:                      
                print("Invalid response format from the remote unit")
            
        # Invalid command/response received
        else:                      
            print("Invalid command/response from the remote unit")

    
    # Receive user input from the USB and send commands to the remote UART
    if usb.poll(0):                    # Check if there is any USB data available
        string = sys.stdin.readline()  # Read one line at a time
        sys.stdin.readline()           # WEIRD! - Needed to avoid a second handling of the same input
        string = string.strip()        # Remove leading and trailing white spaces and control characters from received string
        print("USB   : " + string)     # Echo the USB string on the USB port
        
        # Check if the input is a valid command and if so send it to the remote unit
        if (string == "rd bat" or
            string == "rd group"):
            uart_remote.write(string + "\n")  # Send the command to the remote unit add <LF> terminating character 
        else:                                
            print("Unknown command")   # Command not found so prompt the user
    
    
    gps.receive_nmea_data()            # Receive GPS