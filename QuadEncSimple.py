# Measure edge timing on Pin1, and also pin states Pin1,Pin2
# Track quadrature encoder position using all four edges
# MicroPython for Raspberry Pi Pico (RP2040)
# J.Beale 25-MAR-2021

"""             _______         _______       
P1       ______/       \_______/       \______
            _______         _______         __
P2       __/       \_______/       \_______/  
           A   B   C   D   E   F
           
Time P1 edges (B-D, D-F) with a resolution of 2 * Tclock  (8 ns @ F=250MHz)
also record (P1,P2) levels at 2..4 cycles after each P1 edge

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
    #wait(1,pin,0)   # wait until 1 on input Pin offset 0
    label('loop')
    jmp(pin, 'exit') # jump when inputPin is high
    jmp('loop')
    label('exit')
    
    # ====             send out X counter value
    mov(isr,x)       # transfer X to input shift register
    push()           # transfer shift register to FIFO
    in_(pins, 2)     # read two bits (Pin1,Pin2) into ISR
    push()           # send them to FIFO (also zeroing ISR)
    irq(noblock, 0x10)  # notify main code
                      # input pin is now low
    
                     # wait for Pin(x) to go low
    #wait(0,pin,0)
    label('loop2')
    jmp(pin, 'loop2')  # jump when inputPin is high
    
    # ====            send out X counter value
    mov(isr,x)       # transfer X to input shift register
    push()           # transfer shift register to FIFO
    in_(pins, 2)     # read two bits (Pin1,Pin2) into ISR
    push()           # send them to FIFO (also zeroing ISR)
    irq(noblock, 0x10)  # notify main code
    wrap()
# -----------------------------------------

# monitor falling and rising edges on an input pin
@rp2.asm_pio()
def trackPinOLD():        
    wrap_target()    
    mov(x, 0)       # load X scratch reg. with max value (2^32-1)
    label('start')
    jmp(pin, 'start')  # jump when pin1 is high
    
    jmp(x_dec,'loop1')
    
    # ===== now pin is high: Dec X, exit when pin1 goes low
    label('loop1')
    jmp(x_dec,'continue')  # decrement X, jump if zero
    label('continue')
    jmp(pin, 'loop1')  # jump when pin1 is high 
    # ====             send out X counter value
    mov(isr,x)       # transfer X to input shift register
    push()           # transfer shift register to FIFO
    in_(pins, 2)     # read two bits (Pin1,Pin2) into ISR
    push()           # send them to FIFO (also zeroing ISR)
    irq(noblock, 0x0)  # notify main code
                      # input pin is now low
    mov(x,0)                      
    jmp(x_dec,'loop') # X <- (2^32-1)
                      # ==== Dec X, exit when pin1 goes high
    label('loop')
    jmp(pin, 'exit')  # jump when pin1 is high 
    jmp(x_dec,'loop') # decrement X, jump if zero
    label('exit')
    # ====             send out X counter value
    mov(isr,x)       # transfer X to input shift register
    push()           # transfer shift register to FIFO
    in_(pins, 2)     # read two bits (Pin1,Pin2) into ISR
    push()           # send them to FIFO (also zeroing ISR)
    irq(noblock, 0x0)  # notify main code
    wrap()
# -----------------------------------------

def vBlink(p,t,n):      # blink LED on pin p, duration t milliseconds, repeat n times
    for i in range(n):
        p.value(1)
        utime.sleep_ms(t)
        p.value(0)   # Pico, ESP32: 0 means LED off
        utime.sleep_ms(t)
# -----------------------------------------

def irq_handle(sm):            # handle interrupt
      global stateEnc, uFlag      
      global luTable, countEnc

      sm.get()
      #t = (0xffffffff - sm.get())  # counter value      
      # print(t)
      ps = sm.get()                # pin state P2,P1
      stateEnc = ((stateEnc&0b11)<<2) | ps
      countEnc += luTable[stateEnc]  # count up or down      
      #uFlag |= (sm.id()+1)  # add state machine ID to flag
      uFlag |= (ps & 0b11)  # add bit pattern to flag
    
# ----------------------------------------- 
def main():
    global led1,led2,led3
    global p1   # so p2 interrupt handler can read the pin
    global timeData,pinData,newDataFlag
    global pulsein, pulsein2
    global stateEnc  # 4-bit pin state variable (p2old,p1old,p2new,p1new)
    global uFlag
    global luTable
    global countEnc  # current encoder position

    m.freq(MFREQ)      # set CPU frequency; not necessarily the default 125 MHz       
    uFlag = False    # haven't got any new data yet
    led1 = m.Pin(25, m.Pin.OUT)              # set pin 25 (driving onboard LED) to output
    led2 = m.Pin(22, m.Pin.OUT)              # set external output pin (driving offboard LED) to output
    led3 = m.Pin(21, m.Pin.OUT)              # set external output pin (driving offboard LED) to output
    led1.off()
    led2.off()
    led3.off()
    
    vBlink(led1,100,4)  # blink pattern to indicate program start
    utime.sleep_ms(500)
    vBlink(led1,200,4)
    utime.sleep_ms(1500)
    
    # quadrature encoder pin-state lookup, 4 bit index of last & current value of A,B inputs
    #          0  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15    
    luTable = [0,-1,+1, 0,+1, 0, 0,-1,-1, 0, 0,  +1,  0, +1, -1,  0]  # for both pins P1,P2
    stateEnc = 0
    countEnc = 0
    
    #vBlink(led1,150,3)     # program-starting signal from onboard LED
    
    utime.sleep_ms(100)

    p1 = m.Pin(16,m.Pin.IN, m.Pin.PULL_UP)   # Channel A / Pin1 input
    p2 = m.Pin(17,m.Pin.IN, m.Pin.PULL_UP)   # Channel B / Pin2 input
  
    fsm = int(MFREQ/1000)
    sm0 = rp2.StateMachine(0, trackPin, freq=fsm, in_base=p1, jmp_pin=p1)   # sm 0-3 in first PIO instance
    sm1 = rp2.StateMachine(1, trackPin, freq=fsm, in_base=p1, jmp_pin=p2)

    sm0.irq(irq_handle)
    sm1.irq(irq_handle)
    
    sm0.active(1)
    sm1.active(1)

    print("n,msec,pos")  # CSV header line
    print("# %s" % VERSION)
    lCnt = 0
    pCnt = 0
    dRatio = 1
    while True:
        if uFlag:          # update flag true when new data available
          ms = utime.ticks_ms()
          #if (lCnt % dRatio == 0):
          if True:
            print("%d,%d,%d" % (pCnt,ms,countEnc))
            pCnt += 1
          uFlag = 0
          lCnt += 1
          led1.toggle()       

# ---------  End Main Loop  -----------------------------------------    

main()
