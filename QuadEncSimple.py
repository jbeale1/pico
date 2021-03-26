# Track quadrature encoder position using all four edges
# MicroPython for Raspberry Pi Pico (RP2040)
# J.Beale 26-MAR-2021

"""
A,B output signals from a quadrature encoder
                _______         _______       
A        ______/       \_______/       \______
            _______         _______         __
B        __/       \_______/       \_______/  
           1   2   3   4   5   6  ...
           
Record A, B levels at each transition (1, 2, 3, ...)
Use lookup table to find change in encoder position (+1, 0, -1)

    GP## numbering as per RasPi Pico pinout on p.4 of
https://datasheets.raspberrypi.org/pico/pico-datasheet.pdf
"""

import rp2                 # rp2.PIO, rp2.asm_pio
import machine as m        # m.freq, m.Pin
import utime               # utime.sleep, utime.ticks

#MFREQ = 250000000  # CPU frequency in Hz (typ. 125 MHz; Overclock to 250 MHz)
MFREQ = 125000000  # CPU frequency in Hz (typ. 125 MHz; Overclock to 250 MHz)

VERSION = "Quadrature Readout v0.1 26-March-2021 J.Beale"
# ------------------------------------------------------------

# monitor falling and rising edges on an input pin
@rp2.asm_pio()
def trackPin():
    
    wrap_target()        
                     # wait for Pin(x) to go high
    label('loop')
    jmp(pin, 'exit') # exit loop when inputPin is high
    jmp('loop')
    label('exit')
    
    # ====             send out X counter value
    mov(isr,x)       # transfer X to input shift register
    push()           # transfer shift register to FIFO
    in_(pins, 2)     # read two bits (Pin1,Pin2) into ISR
    push()           # send them to FIFO (also zeroing ISR)
    irq(noblock, 0x10)  # notify main code                      
    
                     # wait for Pin(x) to go low
    label('loop2')
    jmp(pin, 'loop2')  # continue loop while inputPin is high
    
    # ====            send out data on FIFO
    mov(isr,x)       # transfer X to input shift register
    push()           # transfer shift register to FIFO
    in_(pins, 2)     # read two bits (Pin1,Pin2) into ISR
    push()           # send them to FIFO (also zeroing ISR)
    irq(noblock, 0x10)  # notify main code
    wrap()
# -----------------------------------------

def vBlink(p,t,n):      # blink LED on pin p, duration t milliseconds, repeat n times
    for i in range(n):
        p.value(1)
        utime.sleep_ms(t)
        p.value(0)      # Pico, ESP32: 0 means LED off
        utime.sleep_ms(t)
# -----------------------------------------

def irq_handle(sm):            # handle interrupt
      global stateEnc, uFlag      
      global luTable, countEnc

      sm.get()                 # this value reserved for future use
      ps = sm.get()            # pin state P2,P1
      stateEnc = ((stateEnc&0b11)<<2) | ps
      countEnc += luTable[stateEnc]  # count up or down      
      uFlag = 1   # add bit pattern to flag
    
# ----------------------------------------- 
def main():
    global stateEnc  # 4-bit pin state variable (p2old,p1old,p2new,p1new)
    global uFlag     # data update flag
    global luTable   # encoder output lookup table
    global countEnc  # current encoder position

    m.freq(MFREQ)      # set CPU frequency; not necessarily the default 125 MHz       
    uFlag = False    # haven't got any new data yet
    led1 = m.Pin(25, m.Pin.OUT)              # set pin 25 (driving onboard LED) to output
    led1.off()
    
    vBlink(led1,100,4)  # 4 short, 4 long blinks to indicate program start
    utime.sleep_ms(500)
    vBlink(led1,200,4)
    utime.sleep_ms(4000)  # delay allows starting recording program
    
    # quadrature encoder pin-state lookup, 4 bit index of last & current value of A,B inputs
    #          0  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15    
    luTable = [0,-1,+1, 0,+1, 0, 0,-1,-1, 0, 0,  +1,  0, +1, -1,  0]  # for both pins P1,P2

    stateEnc = 0  # initial encoder state
    countEnc = 0  # intiial encoder position

    p1 = m.Pin(16,m.Pin.IN, m.Pin.PULL_UP)   # Channel A / Pin1 input
    p2 = m.Pin(17,m.Pin.IN, m.Pin.PULL_UP)   # Channel B / Pin2 input
  
    fsm = int(MFREQ/1000)  # rate of state machine (up to full CPU frequency)
    sm0 = rp2.StateMachine(0, trackPin, freq=fsm, in_base=p1, jmp_pin=p1)   # sm 0-3 in first PIO instance
    sm1 = rp2.StateMachine(1, trackPin, freq=fsm, in_base=p1, jmp_pin=p2)

    sm0.irq(irq_handle)  # set interrupt handler
    sm1.irq(irq_handle)
    
    sm0.active(1)  # start the state machines running
    sm1.active(1)

    print("n,msec,pos")  # CSV header line
    print("# %s" % VERSION)
    pCnt = 0
    dRatio = 1
    while True:
        if uFlag:          # update flag true when new data available
          uFlag = 0        # reset the flag that interrupt handler set
          ms = utime.ticks_ms()  # current time in milliseconds
          print("%d,%d,%d" % (pCnt,ms,countEnc))
          pCnt += 1           # count how many updates we've printed
          led1.toggle()       # LED on every other reading to show activity

# ---------  End Main Loop  -----------------------------------------    

main()
