# Library to use a 24xx64 EEPROM via I2C
#    By design is the max string length 255 characters
#
# Initialize parameters
#    I2C bus
#    I2C address
#
# Available functions
#    read_byte(addr)                   1 byte
#    write_byte(addr, val)
#
#    read_char(addr)                   1 byte
#    write_char(addr, char)
#
#    read_word(addr)                   2 bytes
#    write_word(addr, val)
#
#    read_integer(addr)                4 bytes
#    write_integer(addr, val)
#
#    read_float(addr)                  4 bytes
#    write_float(addr, val)
#
#    read_string(addr, string)         length + 1, input parameters validated
#    write_string(addr, string)                    input parameters validated
#
#    print(start_addr, count)          input parameters validated
#    clear()

import struct                          # Needed for float handling
from time import sleep_ms              # Needed for timing issues in the EEPROM
          

class EEPROM_24xx64():
    # 24xx64 parameters from the datasheet
    PAGE_SIZE = 32                     # The page size of the 24xx64
    EEPROM_SIZE = 8192                 # 64 kbit -> 8192 bytes
    I2C_ADDRESS = 0x50                 # The default 24xx64 I2C address, but 0x50-0x57 are possible
    I2C_ADDRESS_SIZE = 16              # Address is 16 bits
    

    def __init__(self, i2c_bus, i2c_address = I2C_ADDRESS):
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address


    def read_byte(self, addr):
        val = self.i2c_bus.readfrom_mem(self.i2c_address, addr, 1, addrsize = self.I2C_ADDRESS_SIZE)
        return val[0]


    def write_byte(self, addr, val):
        ba = bytearray(1)
        ba[0] = val
        self.i2c_bus.writeto_mem(self.i2c_address, addr, ba, addrsize = self.I2C_ADDRESS_SIZE)
        sleep_ms(5)                    # Needed due to EEPROM write timing, see datasheet Twc


    def read_char(self, addr):
        val = self.i2c_bus.readfrom_mem(self.i2c_address, addr, 1, addrsize = self.I2C_ADDRESS_SIZE)
        char = chr(val[0])
        return char


    def write_char(self, addr, char):
        ba = bytearray(1)
        ba[0] = ord(char[0])
        self.i2c_bus.writeto_mem(self.i2c_address, addr, ba, addrsize = self.I2C_ADDRESS_SIZE)
        sleep_ms(5)                    # Needed due to EEPROM write timing, see datasheet Twc


    def read_word(self, addr):
        ba = bytearray(2)              # Info: ESP32 uses big endianess
        
        if ((addr % self.PAGE_SIZE) > self.PAGE_SIZE - 2):   # Full word not within the same page so read two single bytes
            ba[0] = self.read_byte(addr)
            ba[1] = self.read_byte(addr + 1)
        else:                          # Full word within the same page
            ba = self.i2c_bus.readfrom_mem(self.i2c_address, addr, 2, addrsize = self.I2C_ADDRESS_SIZE)

        return (ba[0] << 8) + ba[1]


    def write_word(self, addr, val):
        ba = bytearray(2)
        ba[0] = val >> 8               # Info: ESP32 uses big endianess
        ba[1] = val
        
        if ((addr % self.PAGE_SIZE) > self.PAGE_SIZE - 2):   # Full word not within the same page so write four single bytes
            self.write_byte(addr, ba[0])
            self.write_byte(addr + 1, ba[1])
        else:                          # Full word within the same page
            self.i2c_bus.writeto_mem(self.i2c_address, addr, ba, addrsize = self.I2C_ADDRESS_SIZE)
            sleep_ms(5)                # Needed due to EEPROM write timing, see datasheet Twc
        

    def read_integer(self, addr):
        ba = bytearray(4)              # Info: ESP32 uses big endianess
        
        if ((addr % self.PAGE_SIZE) > self.PAGE_SIZE - 4):   # Full integer not within the same page so read four single bytes
            for i in range(4):
                ba[i] = self.read_byte(addr + i)
        else:                          # Full integer within the same page
            ba = self.i2c_bus.readfrom_mem(self.i2c_address, addr, 4, addrsize = self.I2C_ADDRESS_SIZE)

        return (ba[0] << 24) + (ba[1] << 16) + (ba[2] << 8) + ba[3]


    def write_integer(self, addr, val):
        ba = bytearray(4)
        ba[0] = val >> 24              # Info: ESP32 uses big endianess
        ba[1] = val >> 16
        ba[2] = val >>  8
        ba[3] = val
        
        if ((addr % self.PAGE_SIZE) > self.PAGE_SIZE - 4):   # Full integer not within the same page so write four single bytes
            for i in range(4):
                self.write_byte(addr + i, ba[i])
        else:                          # Full integer within the same page
            self.i2c_bus.writeto_mem(self.i2c_address, addr, ba, addrsize = self.I2C_ADDRESS_SIZE)
            sleep_ms(5)                # Needed due to EEPROM write timing, see datasheet Twc

    
    def read_float(self, addr):
        ba = bytearray(4)              # https://docs.python.org/3/library/struct.html ESP32 uses big endianess
        
        if ((addr % self.PAGE_SIZE) > self.PAGE_SIZE - 4):   # Full float not within the same page so read four single bytes
            for i in range(4):
                ba[i] = self.read_byte(addr + i)
        else:                          # Full float within the same page
            ba = self.i2c_bus.readfrom_mem(self.i2c_address, addr, 4, addrsize = self.I2C_ADDRESS_SIZE)

        val = struct.unpack(">f", ba)
        return val[0]


    def write_float(self, addr, val):
        ba = bytearray(struct.pack(">f", val))  # https://docs.python.org/3/library/struct.html ESP32 uses big endianess
        
        if ((addr % self.PAGE_SIZE) > self.PAGE_SIZE - 4):   # Full float not within the same page so write four single bytes
            for i in range(4):
                self.write_byte(addr + i, ba[i])
        else:                          # Full float within the same page
            self.i2c_bus.writeto_mem(self.i2c_address, addr, ba, addrsize = self.I2C_ADDRESS_SIZE)
            sleep_ms(5)                # Needed due to EEPROM write timing, see datasheet Twc 

    
    def read_string(self, addr):
        # Check addr
        if addr < 0 or addr > self.EEPROM_SIZE - 2:# -2 because first address is 0 and length also saved to EEPROM
            return -1

        # Read the string
        length = self.read_byte(addr)  # First read the length of the string
        
        string = ""
        for i in range(length):
            string += chr(self.read_byte(addr + i + 1))  # +1 because start_addr contains the length of the string
            
        return string
    
    
    def write_string(self, addr, string): # Max string length is 255 characters
        # Check input parameters
        if addr < 0 or addr > self.EEPROM_SIZE - 2:# -2 because first address is 0 and length also saved to EEPROM
            return -1

        length = len(string)           # The length of the string
        if length > 255:               # 255 because first address is the length in a single byte
            return -2

        if addr + length > self.EEPROM_SIZE - 2:  # -2 because of length index. Can't save beyond the EEPROM size
            return -3
        
        # Save the string
        self.write_byte(addr, length)  # First save the length of the string
        for i in range(length):
            self.write_byte(addr + i + 1, ord(string[i]))  # +1 because start_addr contains the length of the string
            
        return 0


    # Prints the EEPROM data
    #     Automatically rounds the starting address down to the nearest modulus 16
    #     and rounds count up to the nearest 16 modulus
    #     If input is given it is validated and if invalid the function returns with an error code
    #
    #     Input
    #        start_addr: optional, the starting address to print from
    #        count     : optional, the number of pytes to print
    #
    #     Output
    #        If there is an error the error code is returned
    #        If no error formatted data from the EEPROM, first in hex then the character if possible
    #
    def print(self, start_addr = 0, count = EEPROM_SIZE):
        # Check input parameters
        if start_addr < 0 or start_addr > self.EEPROM_SIZE - 1:# -1 because first address is 0
            return -1
        
        if count < 1 or count > self.EEPROM_SIZE:
            return -2
        
        if start_addr + count > self.EEPROM_SIZE:
            return -3
        
        # Find start address to nearest lower 16 modulus
        sa = start_addr % 16
        if (sa != 0):
            start_addr -= sa
        
        # Find count to nearest upper 16 modulus
        count += sa
        c = count % 16
        if (c != 0):
            count += 16 - c
        
        # Read and print
        for i in range (int(count / 16)):
            print(f"{(start_addr + i * 16):04X}: ", end = '')  # Print hex index
            
            ba = bytearray(16)
            ba = self.i2c_bus.readfrom_mem(self.i2c_address, start_addr + i * 16, 16, addrsize = self.I2C_ADDRESS_SIZE)        # Read the data
            
            # Print hex values
            for j in range (16):
                if j == 8:
                    print(" ", end = '')
                print(f"{ba[j]:02X} ", end = '')

            print("| ", end = '')

            # Print values as characters if possible
            for j in range (16):
                if j == 8:
                    print(" ", end = '')
                if ((ba[j] < 32) or (ba[j] > 126)):  # Handle the non-printable characters
                    print(". ", end = '')
                else:
                    print(f"{chr(ba[j])} ", end = '')
            
            print()
            

    # Clears the entire EEPROM, i.e. setting the factory value to each byte
    #     One page at a time is cleared
    #
    #     Input
    #        None
    #
    #     Output
    #        None
    #
    def clear(self):
        ba = bytearray(self.PAGE_SIZE)
        for i in range (self.PAGE_SIZE):
            ba[i] = 0xFF               # The factory EEPROM clear byte value
        
        for i in range (self.EEPROM_SIZE / self.PAGE_SIZE):
            self.i2c_bus.writeto_mem(self.i2c_address, self.PAGE_SIZE * i, ba, addrsize = self.I2C_ADDRESS_SIZE) # Clear a full page
            sleep_ms(5)                # Needed due to EEPROM write timing, see datasheet Twc
        

# EOF ################################################################################