# A program to scan I2C H/W 0, H/W 2 and software I2C busses
from machine import I2C, Pin, SoftI2C
from time import sleep

###########################################################
# OBJECTS AND VARIABLES
i2cHw0 = I2C(0)  # http://docs.micropython.org/en/latest/esp32/quickref.html#hardware-i2c-bus
i2cHw1 = I2C(1)  # 0: SCL 18, SDA 19; 1: SCL 25, SDA 26
# Don't use the same pins as for the H/W I2C busses at the same time
# If all addresses respond as if there is an I2C device connected then the pull-up resistors are missing
i2cSoftware = SoftI2C(scl = Pin(22), sda = Pin(21))# http://docs.micropython.org/en/latest/esp32/quickref.html#software-i2c-bus

###########################################################
# FUNCTIONS
def i2c_scan(i2c_bus):
    # Print which I2C bus is scanned
    if i2c_bus == i2cHw0:
        print("I2C H/W 0")
    elif i2c_bus == i2cHw1:
        print("I2C H/W 1")
    else:
        print("I2C S/W")
    print("=========")

    # Scan for connected devices
    devicesIdentified = i2c_bus.scan()
    
    # Print the result
    devicesCount = len(devicesIdentified)
    print(f"Total number of devices: {devicesCount}")

    if devicesCount == 112:   # There are 16 reserved addresses, thus not 128!
        print("Looks like the I2C bus pull-up resistors are missing")
    else:
        for i in range(devicesCount):
            print(f"Device found at address: 0x{devicesIdentified[i]:02X}")
    
    print()        # Blank line before next scan

###########################################################
# PROGRAM
print("\nRunning I2C scanner\n")

while True:
    i2c_scan(i2cHw0)
    i2c_scan(i2cHw1)
    i2c_scan(i2cSoftware)        
    
    sleep(1)