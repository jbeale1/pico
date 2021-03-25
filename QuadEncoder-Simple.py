# Measure edge timing on Pin1, and also pin states Pin1,Pin2
# Track quadrature encoder pos'n at P1 edge rate (1/2 resolution)
# MicroPython for Raspberry Pi Pico (RP2040)
# J.Beale 24-MAR-2021

"""             _______         _______       
P1       ______/       \_______/       \______
            _______         _______         __
P2       __/       \_______/       \_______/  
           A   B   C   D   E   F
           
Time P1 edges (B-D, D-F) with a resolution of 2 * Tclock  (8 ns @ F=250MHz)
also record (P1,P2) levels at 2..4 cycles after each P1 edge

  For debug, connect GP22 -> GP17 and GP21 -> GP16
    GP## numbering as per RasPi Pico pinout on p.4 of
https://datasheets.raspberrypi.org/pico/pico-datasheet.pdf
"""

import rp2                 # rp2.PIO, rp2.asm_pio
import machine as m        # m.freq, m.Pin
import utime               # utime.sleep, utime.ticks

MFREQ = 250000000  # CPU frequency in Hz (typ. 125 MHz; Overclock to 250 MHz)
#MFREQ = 125000000  # CPU frequency in Hz (typ. 125 MHz; Overclock to 250 MHz)

selfTest = True #False     # generate simulated quadrature signal

# ------------------------------------------------------------

@rp2.asm_pio()
def pin_timing():

    wrap_target()   
    # ===== now pin1 is high. Dec X, exit when pin1 goes low
    
    label('loop1')
    jmp(x_dec,'continue')  # decrement X, jump if zero
    label('continue')
    jmp(pin, 'loop1')  # jump when pin1 is high 

    # ==== send out X counter value
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
        self.sm = stateMachine
   
    def read_blocking(self, n):
        
        ''' in_base declares the first Pin offset
            jmp_pin declares the one pin used for jmp (not an offset)
        '''
        data = []
        # Each list element is tuple: (X reg timer, PIO pin states)            
        for i in range(n):
            data.append( (0xffffffff-self.sm.get(),self.sm.get()) )
        return data

    def read(self):
        
        ''' in_base declares the first Pin offset
            jmp_pin declares the one pin used for jmp (not an offset)
        '''
        # Return tuple: (X reg timer, PIO pin states)            
        return ( (0xffffffff-self.sm.get(),self.sm.get()) )        
    

# -----------------------------------------

def vBlink(p,t,n):      # blink LED on pin p, duration t milliseconds, repeat n times
    for i in range(n):
        p.value(1)
        utime.sleep_ms(t)
        p.value(0)   # Pico, ESP32: 0 means LED off
        utime.sleep_ms(t)
# -----------------------------------------
def tickT1(timer):  # timer callback to blink ext. LED
    global led2
    led2.toggle()
    #print("A:%d" % utime.ticks_ms())

def tickT2(timer):  # timer callback to blink ext. LED
    global led3, led1
    led1.toggle()
    led3.toggle()
    #print("B:%d" % utime.ticks_ms())
          
# ----------------------------------------- 
def main():
    global led1,led2,led3
    global p1   # so p2 interrupt handler can read the pin
    global timeData,pinData,newDataFlag
    global pulsein, pulsein2
    global inState  # 4-bit pin state variable (p2old,p1old,p2new,p1new)    
        
    m.freq(MFREQ)      # set CPU frequency; not necessarily the default 125 MHz       
    newDataFlag = False    # haven't got any new data yet
    led1 = m.Pin(25, m.Pin.OUT)              # set pin 25 (driving onboard LED) to output
    led2 = m.Pin(22, m.Pin.OUT)              # set external output pin (driving offboard LED) to output
    led3 = m.Pin(21, m.Pin.OUT)              # set external output pin (driving offboard LED) to output
    led1.off()
    led2.off()
    led3.off()
    
    # quadrature encoder pin-state lookup, 4 bit index of last & current value of A,B inputs
    #          0  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15    
    luTable = [0, 0, 0,-1, 0, 0, 1, 0, 0, 1, 0,  0,  -1, 0,  0,   0]   # tracking P1 only
    #luTable = [0,-1,+1, 0,+1, 0, 0,-1,-1, 0, 0,  +1,  0, +1, -1,  0]  # for both pins P1,P2
    
    vBlink(led1,150,3)     # program-starting signal from onboard LED
    print("Edge Timer v0.01 24-March-2021 J.Beale")
    utime.sleep_ms(500)

    p1 = m.Pin(16,m.Pin.IN, m.Pin.PULL_UP)   # Channel A / Pin1 input
    #p2 = m.Pin(17,m.Pin.IN, m.Pin.PULL_UP)   # Channel B / Pin2 input
    
    sm0 = rp2.StateMachine(0, pin_timing, in_base=p1)        
    pulsein = pulseTimer(p1,sm0)          # timer to look for ChA signals
    sm0.init(pin_timing,freq=MFREQ,in_base=(p1),jmp_pin=(p1))        
    sm0.exec("mov(x,0)")         # init X register before running
    sm0.active(1)   # start state machines running here


    if selfTest:
      #  -------------------  testing: simulate quadrature signal on output pins
      tim1 = m.Timer()
      tim2 = m.Timer()

      tFreq = 100
      tim1.init(freq=tFreq, mode=m.Timer.PERIODIC, callback=tickT1)  # blink at this rate
      utime.sleep_ms(int(500/tFreq))
      tim2.init(freq=tFreq, mode=m.Timer.PERIODIC, callback=tickT2)  # blink at this rate
      # --------------------------
   
    pulsein.read()                      # first call inaccurate; SM not yet synced to an edge
    (oldTick,inState) = pulsein.read()  # get the new values    
    b32 = 1<<32
    lCnt = 0
    encPos = 0                   # current encoder position
    dRatio = 2                 # sample decimation ratio (print 1 out of dRatio readings)
    errCount = 0               # how many encoder errors detected
    
# ---------  Main Loop  -----------------------------------------    
    while True:   # main loop
      lCnt += 1
      pFlag = (lCnt % dRatio == 0)
      #pFlag = True
      if pFlag:
          tms = utime.ticks_ms()
          print("%d,%d," % (lCnt,tms),end="")

      if True:
#      for i in range(2):
          (newTick,pinData) = pulsein.read()  # get the new values
          inState = ((inState & 0b11)<<2) | pinData & 0b11  # update pin state variable
          inc = luTable[inState]
          encPos += inc
          if (inc == 0):
              errCount += 1

          deltaT = (4 + newTick - oldTick) % b32
          durS = 2*deltaT/(MFREQ)   # duration in seconds
          if pFlag:
              print("%d,%09.7f,%d,%d," % (deltaT,durS,inState,errCount),end="")
          oldTick = newTick
      if pFlag:
          print("%d" % encPos)
          #print()
    
# ---------  End Main Loop  -----------------------------------------    

main()
