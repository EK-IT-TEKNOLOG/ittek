from machine import ADC, Pin, PWM
from time import sleep

# LMT84 datasheet
# V = (-5.50 mV/°C) T + 1035 mV
# T = (V - 1035 mV) / (-5.5 mV/°C)
alpha = -5.5
beta = 1035

###########################################################
# CONFIGURATION
pin_lmt84 = 35

adc2mV = 2050.0 / 4095.0

average = 1                            # The number of averages used

###########################################################
# OBJECTS
adc_lmt84 = ADC(Pin(pin_lmt84))             
adc_lmt84.atten(ADC.ATTN_6DB)

###########################################################
# PROGRAM

print("LMT84 test\n")

while True:
    adcVal = 0
    
    if average > 1:
        for i in range (average):
            adcVal += adcLmt84.read()
            sleep(1 / average)
        adcVal = adcVal / average
    else:
        adcVal = adcLmt84.read()
        sleep(1)

    mV = adc2mV * adcVal
    temp = (mV - beta) / alpha
    print(f"ADC: {adcVal:3} -> {temp:,.1} °C")
    