from machine import Pin, I2C, PWM
from DIYables_MicroPython_LCD_I2C import LCD_I2C
from time import sleep

led1 = PWM(Pin(12, Pin.OUT), duty=0, freq=200)
led2 = PWM(Pin(21, Pin.OUT), duty=0, freq=200)

# CONFIGURATION
# The MCP3021 I2C address
deviceAddresses = [0x4B, 0x48]

# The ADC to voltage ratio (the voltage divider).
# To find it make a single measurement and make a note
# of the voltage (voltmeter) and ADC (program) values.
# Then calculate Unom = 1023 * Ureal / ADCvalue.
uNom = 6.5


# PROGRAM
i2c = I2C(0)

devicesIdentified = i2c.scan()

deviceAddresses = [i for i in devicesIdentified if not i == 0x27]
I2C_ADDR = 0x27

# Define the number of rows and columns on your LCD
LCD_ROWS = 4
LCD_COLS = 20

# Initialize LCD
lcd = LCD_I2C(i2c, I2C_ADDR, LCD_ROWS, LCD_COLS)

# Setup function
lcd.backlight_on()
lcd.clear()

def get_adc_val(deviceAddress):
    # Measure and get the two bytes from the ADC
    adcBytes = i2c.readfrom(deviceAddress, 2)
    
    # Put the bytes in UpperDataByte and LowerDataByte
    UpperDataByte = int(adcBytes[0])
    LowerDataByte = int(adcBytes[1])
    
    # Print the raw received bytes
    print("ADC Upper Data Byte: 0x%02X" % UpperDataByte)
    print("ADC Lower Data Byte: 0x%02X" % LowerDataByte)
    
    # Step B1, merge UpperDataByte with LowerDataByte
    combinedBytes = (UpperDataByte << 8) + LowerDataByte
    print("combinedBytes D9-D0: 0x%04X" % combinedBytes)
    
    # Step B2, right justify the combined bytes
    adcValue = combinedBytes >> 2
    print("adcValue, hex      : 0x%04X" % adcValue)
    print("adcValue, dec      : %d" % adcValue)
    
    # Calculate the voltage
    voltage = adcValue * uNom / 1023.0
    print("Voltage            : %.2f V" % voltage)
    
    return adcValue

def error_func():
    while True:
        led1.duty(0)
        sleep(0.3)
        led1.duty(1024)
        sleep(0.3)

if not len(deviceAddresses) == 2:
    print(f'[-] Der blev fundet {len(deviceAddresses)} devices. Der blev forventet at finde 2. {str(deviceAddresses)}')
    lcd.clear()
    lcd.set_cursor(0, 0)
    lcd.print(f'[-] Der blev fundet {len(deviceAddresses)} devices. Der blev forventet at finde 2. {str(deviceAddresses)}')
    error_func()

while True:
    lcd.clear()
    lcd.set_cursor(0,0)
    lcd.print('ADC Adapter Tester')
    for dev_addr in deviceAddresses:
        val = get_adc_val(dev_addr)
        idx = deviceAddresses.index(dev_addr)

        if idx == 0:
            lcd.set_cursor(idx+1,0)
            led1.duty(val)
        else:
            lcd.set_cursor(idx+2,0)
            led2.duty(val)
        lcd.print(f'{dev_addr}: {val}')

        # Pause before next measurement
        sleep(.3)
        print()

