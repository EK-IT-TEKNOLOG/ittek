# A simple program to light LED1 up using either an analog or digital voltage or PWM
from machine import DAC, Pin, PWM

###########################################################
# CONFIGURATION
pin_led1 = 26

mode = "DIGITAL"                       # Mode: "ANALOG", "DIGITAL", "PWM"

###########################################################
# PROGRAM
print(f"LED1 test program, {mode}\n")

if mode == "ANALOG":
    led1_analog = DAC(Pin(pin_led1))   # Create DAC object for the pin
    led1_analog.write(128)             # Set the DAC voltage, 0-255, e.g. 1.65 V -> 128

elif mode == "DIGITAL":
    led1_digital = Pin(pin_led1, Pin.OUT) # Create digital pin object
    led1_digital.value(1)              # Set pin on/high

elif mode == "PWM":
    led1_pwm = PWM(Pin(pin_led1))      # Create PWM object for the pin
    led1_pwm.freq(40)                  # Set PWM frequency    
    led1_pwm.duty(512)                 # Set the duty cycle, 0-1023, e.g. 50% -> 512
    
else:
    print("ERROR: Undefined mode. Please use only: ANALOG, DIGITAL or PWM")
