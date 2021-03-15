'''
Read the time delay between 2 input pulses, using PIO state machine hardware
RP2040 CPU clock at 250 MHz
based on code by Daniel Perron March 2021
https://www.raspberrypi.org/forums/viewtopic.php?p=1831725#p1831725
mods J.Beale 14-March-2021
'''

import utime
import rp2
from rp2 import PIO, asm_pio
from machine import Pin
    
'''
              ______       _____      _____
pin 1 _______/      \_____/     \____/    
             A                       B
             
  Time A-B interval:
  wait for 1st rising edge on pin 1, then run timer until falling edge, 
   and until 2nd rising edge, and until 2nd falling edge,
   and until 3rd rising edge. Report accumulated count.
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
    wait(0,pin,0)     # wait for pin1 to be low (if isn't already)
    wait(1,pin,0)     # wait for pin1 to be high: first rising edge

    # Here, just had rising edge; pin1 is high
    # Now, dec x while pin1 remains high
    label('loop')
    jmp(x_dec,'continue')  # decrement X, jump if zero
    label('continue')
    jmp(pin, 'loop')       # jump when 'pin' (config as pin1=GPIO16) is high 

    # here, just had falling edge. pin1 is low
    # dec x until pin1 goes high
    label('loop2')
    jmp(pin, 'exit')       # jump when 'pin' (config as pin1=GPIO16) is high        
    jmp(x_dec,'loop2')     # decrement X, jump if zero
    label('exit')

    # Here, just had 2nd rising edge; pin1 is high
    # Now, dec x while pin1 remains high
    label('loop3')
    jmp(x_dec,'cont2')  # decrement X, jump if zero
    label('cont2')
    jmp(pin, 'loop3')       # jump when 'pin' (config as pin1=GPIO16) is high 

    # here, just had 2nd falling edge; pin1 is low
    # dec x until pin1 goes high
    label('loop4')
    jmp(pin, 'exit2')       # jump when 'pin' (config as pin1=GPIO16) is high        
    jmp(x_dec,'loop4')     # decrement X, jump if zero
    label('exit2')

    # Now report value to CPU via FIFO, with push
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
        self.sm.init(PULSE_LOW_DELTA,freq=250000000,
                     in_base=(self.pin1),
                     jmp_pin=(self.pin2))
        
        ''' in_base declare the first Pin offset
            jmp_pin declare the pin to use for jmp (this is not an offset)
        '''
        self.sm.active(1)
        return (0xffffffff- self.sm.get()) # units of raw counter ticks, T = 1/freq
    

if __name__ == "__main__":
    #from machine import Pin    
    import machine as m
    import utime
    
    m.freq(250000000) # overclock to 250 MHz. Wheee!
    #m.freq(125000000) # standard clock speed

    p1 = m.Pin(16,m.Pin.IN, m.Pin.PULL_UP) # Channel A input
    # p2 = Pin(17,Pin.IN, Pin.PULL_UP) # Channel B input
    led1 = m.Pin(25, m.Pin.OUT)              # set pin 25 (driving onboard LED) to output
    led2 = m.Pin(22, m.Pin.OUT)              # set external output pin (driving offboard LED) to output
    led1.off()
    led2.off()

    pulsein = pulsedelay(p1,p1) 

    lastVal = pulsein.get()  # get P1-P2 interval time
    rSum = 0  # running sum of interval deltas
    while True:
        newVal = pulsein.get()    # A-B interval
        delta = newVal - lastVal
        lastVal = newVal
        rSum += delta
        print("%d, %d" % (newVal, rSum))
        led1.toggle()

# Note: Timer Period = 2/(250 MHz) so time in microseconds = newVal / (125) 
