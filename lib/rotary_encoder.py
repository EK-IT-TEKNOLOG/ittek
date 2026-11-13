from machine import Pin

CW = 1                                 # Constant clock wise rotation
CCW = -1                               # Constant counter clock wise rotation

class RotaryEncoder:
    def __init__(self, pin_enc_a, pin_enc_b):
        self.pin_enc_a = pin_enc_a
        self.pin_enc_b = pin_enc_b
        self.rotenc_A = Pin(pin_enc_a, Pin.IN, Pin.PULL_UP)
        self.rotenc_B = Pin(pin_enc_b, Pin.IN, Pin.PULL_UP)
        self.enc_state = 0
        
    def re_half_step(self):        
        encTableHalfStep = [
            [0x03, 0x02, 0x01, 0x00],
            [0x23, 0x00, 0x01, 0x00],
            [0x13, 0x02, 0x00, 0x00],
            [0x03, 0x05, 0x04, 0x00],
            [0x03, 0x03, 0x04, 0x10],
            [0x03, 0x05, 0x03, 0x20]]    
        
        self.enc_state = encTableHalfStep[self.enc_state & 0x0F][(self.rotenc_B.value() << 1) | self.rotenc_A.value()]
     
        # -1: Left/CCW, 0: No rotation, 1: Right/CW
        result = self.enc_state & 0x30
        if (result == 0x10):
            return CW
        elif (result == 0x20):
            return CCW
        else:
            return 0


    def re_full_step(self):
        encTableFullStep = [
            [0x00, 0x02, 0x04, 0x00],
            [0x03, 0x00, 0x01, 0x10],
            [0x03, 0x02, 0x00, 0x00],
            [0x03, 0x02, 0x01, 0x00],
            [0x06, 0x00, 0x04, 0x00],
            [0x06, 0x05, 0x00, 0x20],
            [0x06, 0x05, 0x04, 0x00]]

        self.enc_state = encTableFullStep[self.enc_state & 0x0F][(self.rotenc_B.value() << 1) | self.rotenc_A.value()]
     
        # -1: Left/CCW, 0: No rotation, 1: Right/CW
        result = self.enc_state & 0x30
        if (result == 0x10):
            return CW
        elif (result == 0x20):
            return CCW
        else:
            return 0 
    
