'''
Read the time delay between 2 input pulses, using PIO state machine hardware
RP2040 CPU clock at 125 MHz
based on code by Daniel Perron March 2021
https://www.raspberrypi.org/forums/viewtopic.php?p=1831725#p1831725
mods J.Beale 6-March-2021
'''

import utime
import rp2
from rp2 import PIO, asm_pio
from machine import Pin
    
'''
              ______
pin 1 _______/      \_________

                 ______
pin 2 __________/      \_________
  
  wait for rising edge on pin 1
  run timer until rising edge on pin 2
'''    
    
# Assembly code for RP2040 PIO hardware state machine
@asm_pio()
def PULSE_LOW_DELTA():
    # clock set at 100MHz
    
    # Initialize x to be -1
    set(x,0)
    jmp(x_dec,'START')
    label('START')

    # Syntax: wait(Polarity,Source,Index)
    # https://datasheets.raspberrypi.org/rp2040/rp2040-datasheet.pdf#section_pio
    wait(0,pin,0)     # wait for pin1 to be low    
    wait(1,pin,0)     # wait for pin1 to be high
        
    # Here, have found pin1 rising edge.
    # Now, dec x while pin2 is low
    label('loop')    
    jmp(pin, 'exit')   # exit loop when 'pin' (config as pin2=GPIO17) is high    
    jmp(x_dec,'loop')  # decrement X and start loop again    
    label('exit')
    
    # Found rising edge on pin2. Now report value to CPU via FIFO, with push
    mov(isr,x) # transfer X to input shift register
    push()  # transfer shift register to FIFO
    label('End')
    jmp('End')  # stop activity

# regular Python code follows

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
        return (0xffffffff- self.sm.get()) # units of raw counter ticks, T = 1/freq
    

if __name__ == "__main__":
    from machine import Pin    
    import utime
    
    p1 = Pin(16,Pin.IN, Pin.PULL_UP) # Channel A input
    p2 = Pin(17,Pin.IN, Pin.PULL_UP) # Channel B input

    pulsein = pulsedelay(p1,p2) 

    lastVal = pulsein.get()  # get P1-P2 interval time
    rSum = 0  # running sum of interval deltas
    while True:
        newVal = pulsein.get()    # P1-P2 interval
        delta = newVal - lastVal
        lastVal = newVal
        rSum += delta
        print("%d, %d" % (newVal, rSum))

# Note: Timer Period = 2/(125 MHz) so time in microseconds = newVal / (62.5) 
