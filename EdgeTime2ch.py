# Measure edge timing on Pin1, and also pin states Pin1,Pin2
# MicroPython for Raspberry Pi Pico (RP2040)
# J.Beale 22-MAR-2021

"""             _______         _______       
P1       ______/       \_______/       \______
            _______         _______         __
P2       __/       \_______/       \_______/  
           A   B   C   D   E   F
           
Time P1 edges (B-D, D-F) with a resolution of 2 * Tclock  (8 ns @ F=250MHz)
also record (P1,P2) levels at 2..4 cycles after each P1 edge
"""

import rp2                 # rp2.PIO, rp2.asm_pio
import machine as m        # m.freq, m.Pin
import utime               # utime.sleep

MFREQ = 250000000  # CPU frequency in Hz (typ. 125 MHz; Overclock to 250 MHz)

# ------------------------------------------------------------

@rp2.asm_pio()
def pin_timing():

    mov(x,0)          # init could be done with _sm.exec() from caller   
    wait(0,pin,0)     # wait for pin1 to be low (if isn't already)
    wait(1,pin,0)     # wait for pin1 to be high: first rising edge    
    jmp(x_dec,'loop1') # start main loop

    wrap_target()
    
    # ===== now pin1 is high. Dec X, exit when pin1 goes low
    
    label('loop1')
    jmp(x_dec,'continue')  # decrement X, jump if zero
    label('continue')
    jmp(pin, 'loop1')  # jump when pin1 is high 

    # ==== send out two words: (X counter value, state of Pin1, Pin2 )

    mov(isr,x)    # transfer X to input shift register
    push()        # transfer shift register to FIFO    
    in_(pins, 2)  # read two bits (Pin1,Pin2) into ISR
    push()        # send them to FIFO (also zeroing ISR)

    # ===== now pin1 is low. Dec x, exit when pin1 goes high
    
    label('loop2')
    jmp(pin, 'exit')   # jump when pin1 is high        
    jmp(x_dec,'loop2') # decrement X, jump if zero
    jmp('loop2')       # keep going, if it rolls over
    label('exit')

    # ==== send out two words: (X counter value, state of Pin1, Pin2 )

    mov(isr,x)    # transfer X to input shift register
    push()        # transfer shift register to FIFO    
    in_(pins, 2)  # read two bits (Pin1,Pin2) into ISR
    push()        # send them to FIFO (also zeroing ISR)

    wrap()
    
    
# ---------------------------------------------------------------------

class pulseTimer:

# Instantiate StateMachine(0) with PIO program on Pin(16).

    def __init__(self, pin1, stateMachine=0):
        self.pin1 = pin1
        self.sm = rp2.StateMachine(0, pin_timing, in_base=pin1)                
        self.sm.init(pin_timing,freq=MFREQ,
                     in_base=(self.pin1),
                     jmp_pin=(self.pin1))
        self.sm.active(1)   # start state machine running here
        
    def read_blocking(self, n):
        
        ''' in_base declares the first Pin offset
            jmp_pin declares the one pin used for jmp (not an offset)
        '''
        data = []
        # Each list element is tuple: (X reg timer, PIO pin states)            
        for i in range(n):
            data.append( (0xffffffff-self.sm.get(),self.sm.get()) )
        return data

# -----------------------------------------

def vBlink(p,t,n):      # blink LED on pin p, duration t milliseconds, repeat n times
    for i in range(n):
        p.value(1)
        utime.sleep_ms(t)
        p.value(0)   # Pico, ESP32: 0 means LED off
        utime.sleep_ms(t)
# -----------------------------------------
          
def main():
    m.freq(MFREQ) # set CPU frequency; not necessarily the default 125 MHz       

    p1 = m.Pin(16,m.Pin.IN, m.Pin.PULL_UP)   # Channel A / Pin1 input    
    led1 = m.Pin(25, m.Pin.OUT)              # set pin 25 (driving onboard LED) to output
    led2 = m.Pin(22, m.Pin.OUT)              # set external output pin (driving offboard LED) to output
    led1.off()
    led2.off()
    vBlink(led1,150,3)     # program-starting signal from onboard LED
    utime.sleep_ms(500)

    pulsein = pulseTimer(p1) 

    edges = 8   # how many edges to get at one time
    lcount = 0  # how many lines total sent
    pcount = 0  # how many packets sent (printed)
    
    (oldTicks,oldPins) = pulsein.read_blocking(1)[0]  # first call sets previous values
    oldPins = oldPins << 2
    
    maxTimerCount = 1<<32  # 32 bit counter rolls over here  2^32 = 4,294,967,296
    
    while True:   # main loop
        vBlink(led1,10,1)     # program-starting signal from onboard LED
        newVals = pulsein.read_blocking(edges)  # get interval times and pin states        
        lcount += 1
        #print(newVals) # DEBUG
        i = 0
        outs = ("%d," % lcount)
        for (n,pVal) in newVals:
            ticks = (n + 2*i)           # +2*i correction from (mov,push,in,push) overhead
            delta = (ticks - oldTicks) % maxTimerCount            
            # outs += ("%d" % delta) + "," + '{0:d},{0:02b}'.format(delta,pVal)
            pVals = (oldPins & 0b1100) | (pVal & 0b0011)
            outs += '{0:d},{1:04b}'.format(delta,pVals)
            oldTicks = ticks
            oldPins = pVal << 2
            i += 1
            if i != edges: 
                outs += ","
        # outs += str(oldTicks)
        oldTicks = (oldTicks - 2*i) % maxTimerCount
        outs += '\n'         # end of line char concludes each line
        # uart.write(outs)
        print(outs,end='')
        pcount += 1        
    

    # sm0.active(1)   # Start the StateMachine running.
"""    
    p.392 https://datasheets.raspberrypi.org/rp2040/rp2040-datasheet.pdf
    Write Register IO:CTRL Register:SM_ENABLE  set the enable bits (3..0) which starts the respective state machines.
    0x03 would start both SM 0 and SM 1 at the same time.
"""    
# ------------------------------

main()
