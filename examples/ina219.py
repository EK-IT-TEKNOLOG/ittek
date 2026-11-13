# A dynamic current measuring program using an INA219
from machine import I2C
from ina219_lib import INA219
import time
from time import sleep

###########################################################
# CONFIGURATION
i2c_port = 0                           # The I2C port number, and thus pins

ina219_i2c_addr = 0x40                 # The INA219 I2C address

delimiter = '\t'                       # The dump delimiter

#########################################################################
# OBJECTS
i2c = I2C(i2c_port)                    # I2C bus

ina219 = INA219(i2c, ina219_i2c_addr)  # The INA219 object

#########################################################################
# VARIABLES
cur_max = -9999                        # The max current
cur_min = 9999                         # The min current
cur_sum = 0                            # The sum of current measurements

measurements = 0                       # Number of measurements 

###########################################################
# PROGRAM
print("\nINA219 dynamic current monitoring program\n")

ina219.set_calibration_16V_400mA()     # Set a more sensitive range

while True:
    # Get the values
    current = ina219.get_current()
    shunt_voltage = ina219.get_shunt_voltage()
    bus_voltage = ina219.get_bus_voltage()
    
    # Update the flow variables
    measurements += 1                  # Increment the counter
    timestamp = time.ticks_ms()        # Get the relative time stamp
    
    # Check min, max and calc average
    if current < cur_min:
        cur_min = current
    elif current > cur_max:
        cur_max = current
        
    cur_sum += current
    cur_avg = cur_sum / measurements
    
    # Print the data (ought to be to a file instead)
    print(f"{measurements}{delimiter}{timestamp}{delimiter}{bus_voltage}{delimiter}{current}")
    
    print(f"\t\t\t\t\t\t{cur_min:,.2} {cur_max:,.2} {cur_avg:,.2}")
    
    sleep(0.2)                         # Should not be present. Measure as fast as possible
