from machine import Pin
from time import sleep

from adc_sub import ADC_substitute

# ADC.ATTN_0DB  : No attenuation (100 mV - 950 mV)
# ADC.ATTN_2_5DB: 2.5 dB attenuation (100 mV - 1250 mV)
# ADC.ATTN_6DB  : 6 dB attenuation (150 mV - 1750 mV)
# ADC.ATTN_11DB : 11 dB attenuation (150 mV - 2450 mV)
# adc = ADC(Pin(25))
# adc.atten(ADC.ATTN_11DB)
# 
# print("ADC tester\n")
# 
# while True:
#     adcVal = 0
#     
#     for i in range (256):
#         adcVal += adc.read()
#         #sleep(0.05)
#     adcVal = adcVal >> 8
# 
#     print("ADC: %4d, %.4f V" % (adcVal, adcVal * 3.3 / 4095))
#     sleep(1)
#

adc = ADC_substitute(25)

while True:
    a = adc.read_adc()
    v = adc.read_voltage()
    print("ADC: {a:4}, {v:,.2} V" % (a, v))

#     v = 0.000838616 * a + 0.079035
#     print("ADC: %4d, %.4f V" % (a, v))
    
   
    sleep(1)
    