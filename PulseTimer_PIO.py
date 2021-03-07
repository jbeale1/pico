''' Read the time delay between 2 input pins going low. RP2040 CPU clock at 125 MHz
by Daniel Perron March 2021
https://www.raspberrypi.org/forums/viewtopic.php?p=1831725#p1831725

mods J.Beale 6-March-2021
'''

import utime
import rp2
from rp2 import PIO, asm_pio
from machine import Pin
    
'''
pin 1 _______              _________
             \____________/

pin 2 ____________        ________
                 \______/
             
       A   B  C   D
  
  
  A= be sure that pin2 is high
  B= be sure that pin1 is high
  C= detect pin 1 is low (dec X)
  D= detect pin 2 is low
'''    
    
# Assembly code for RP2040 PIO hardware state machine
@asm_pio()
def PULSE_LOW_DELTA():
    # clock set at 100MHz
    
    # Initialize x to be -1
    set(x,0)
    jmp(x_dec,'P2_LOW')

    # Wait for pin2 to be high
    label('P2_LOW')
    jmp(pin,'P2_HIGH')  # jumps if 'pin' is high
    jmp('P2_LOW')
    label('P2_HIGH')
    
    #wait for pin1 to be high
    wait(1,pin,0)
    
    #wait for pin1 to be low
    wait(0,pin,0)
    
    #ok we got low just dec x until pin2 is low
    label('loop')
    #decX
    jmp(x_dec,'loopCount')
    label('loopCount')
    jmp( pin, 'loop')
    
    #ok we got Pin 2 low! register it by push
    mov(isr,x) # transfer X to input shift register
    push()  # transfer shift register to FIFO
    label('End')
    jmp('End')  # stop activity

# regular Python code    

class pulsedelay:
    
    def __init__(self,pin1,pin2, stateMachine=0):
        self.pin1 = pin1
        self.pin2 = pin2
        self.sm= rp2.StateMachine(stateMachine)

    def get(self):
        self.sm.init(PULSE_LOW_DELTA,freq=125000000,
                     in_base=(self.pin1),
                     jmp_pin=(self.pin2))
        
        ''' in_base declare the first Pin offset
            jmp_pin declare the pin to use for jmp (this is not an offset)
        '''
        self.sm.active(1)
        # adjust for microsecond value
        return (0xffffffff- self.sm.get()) / 62.5


if __name__ == "__main__":
    from machine import Pin    
    import utime
    
    p1 = Pin(16,Pin.IN, Pin.PULL_UP) # Channel A input
    p2 = Pin(17,Pin.IN, Pin.PULL_UP) # Channel B input

    pulsein = pulsedelay(p1,p2) 

    lastVal = pulsein.get()  # get P1-P2 interval time
    while True:
        newVal = pulsein.get()    # P1-P2 interval
        delta = newVal - lastVal
        lastVal = newVal
        print(newVal,",","%.3f" % round(delta,3))        
