# A simple rotary encoder test program
from rotary_encoder import RotaryEncoder, CW, CCW

###########################################################
# CONFIGURATION
# Rotary encoder pins, actual A or B depends the rotary encoder hardware. If backwards swap the pin numpers
pin_enc_a = 36
pin_enc_b = 39

counter = 0

#########################################################################
# OBJECTS
rotary_enc_obj = RotaryEncoder(pin_enc_a, pin_enc_b)
       
###########################################################
# PROGRAM
print("Rotary encoder test program\n")
        
while True:
    # Read the rotary encoder
    res = rotary_enc_obj.re_full_step()               # or: re_half_step()

    # Direction and counter
    counter += res

    if res == CW:
        print(f"Right/CW: {counter}")
    elif res == CCW:
        print(f"Left/CCW: {counter}")


