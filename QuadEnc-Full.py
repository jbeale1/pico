# Track quadrature encoder position using all four edges
# MicroPython for Raspberry Pi Pico (RP2040)
# based on https://www.raspberrypi.org/forums/viewtopic.php?p=1842706#p1842706
# J.Beale 28-MAR-2021

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

from machine import Pin, mem32
from rp2 import asm_pio, StateMachine, PIO
from time import ticks_ms, ticks_us, ticks_diff, sleep, sleep_ms
import array

MFREQ = 200_000_000  # CPU frequency in Hz (typ. 125 MHz; Overclock to 250 MHz)
VERSION = "Quadrature Readout v0.21 28-March-2021 J.Beale"

# -----------------------------------------
def vBlink(p,t,n):      # blink LED on pin p, duration t milliseconds, repeat n times
    for i in range(n):
        p.value(1)
        sleep_ms(t)
        p.value(0)      # Pico, ESP32: 0 means LED off
        sleep_ms(t)
# -----------------------------------------

# generate a 2-cycle flag signal after every input edge
# one instance of SM will watch Ch.A, the other Ch.B
@asm_pio(set_init=PIO.OUT_HIGH)  
def trigger():
    wait(1, pin, 0)  # wait for input pin to go high
    set(pins, 1) [2] # set flag bit for 2 cycles
    set(pins, 0)     # and return it low
    wait(0, pin, 0)  # wait for input pin to go low
    set(pins, 1) [2] # set flag bit for 2 cycles
    set(pins, 0)     # and return it low
                     # and loop around again

@asm_pio(sideset_init=PIO.OUT_LOW)
def counter():    
    wait(1, pin, 2)    # initial synchronization with edge flag
    
    wrap_target()       # -- top of main r (run-forever) loop    
    label("loop")       # --- top of inner 4-cycle loop
    set(x, 0) .side(0)  
    wait(0, pin, 2)     # continue when edge flag low (it almost always is)
    in_(pins, 2)
    push()              # note that PUSH can stall if FIFO fills
    jmp(x_dec, "counter_start")
    
    label("counter_start")      # inner 2-cycle timing loop
    jmp(pin, "output")          # runs until edge flag goes high
    jmp(x_dec, "counter_start")
    label("output")
    
    mov(isr, invert(x)) .side(1)
    push()    
    
    irq(noblock, 0x10)   # signal 2 words of data are now ready to read    
    wrap()               # ----- repeat forever

ASIZE = 1023                        # size of circular data buffers (dataT, dataB)
dataT = array.array("I", [0]*ASIZE)  # store UINT32 timing data
dataB = array.array("B", [0]*ASIZE)  # store UCHAR bits (Ch.A, Ch.B values)
dIdx = 0                         # curent index into DATA array

def counter_handler(sm):
    global dIdx
    dataB[dIdx] = sm.get() & 0b11    # read chA,chB
    dataT[dIdx] = sm.get() + 4       # read timer value
    dIdx = (dIdx + 1) % ASIZE           # increment index in circular buffer
    
# --------------------------------------------
def main():
  global start
  global stateEnc
  global posEnc
  global luTable   # encoder output lookup table
  global led1
  global dIdx      # index into data buffers, updated in interrupt routine

  machine.freq(MFREQ)
  led1 = Pin(25, Pin.OUT)
  led1.off()

  vBlink(led1,100,4)  # 4 short, 4 long blinks to indicate program start
  sleep_ms(500)
  vBlink(led1,200,4)
  sleep_ms(4000)  # delay allows starting recording program
    
  print("pos,ticks")       # CSV header line
  print("# %s" % VERSION)
    
  posEnc= 0
  stateEnc = 0  # 4-bit encoder state (P2old,P1old,P2new,P1new)
  luTable = [0,-1,+1, 0,+1, 0, 0,-1,-1, 0, 0,  +1,  0, +1, -1,  0]  # for both pins P1,P2
  start = ticks_us()

  chA = Pin(14,Pin.IN,Pin.PULL_UP)  # encoder A input signal
  chB = Pin(15,Pin.IN,Pin.PULL_UP)  # encoder B input signal
  chFlag = Pin(16)  # Flag signal, goes high for 2 cycles when chA or chB edge detected

  smf = int(MFREQ/1)  # was 200M
  sm2 = StateMachine(2, trigger, freq=smf, in_base=chA, set_base = chFlag)  # watch Ch.A
  sm2.active(1)
  sm3 = StateMachine(3, trigger, freq=smf, in_base=chB, set_base = chFlag)  # watch Ch.B
  sm3.active(1)
                   # count time between edges on both Ch.A and Ch.B
  sm4 = StateMachine(4, counter, freq=smf, in_base=chA, jmp_pin = chFlag, sideset_base=Pin(22))
  sm4.irq(counter_handler)

  sm4.active(1)

  i = 0  # starting index into data arrays
  while True:  # all the action is in the interrupt routine
      if (dIdx != i):  # any new data in the buffer?
          stateEnc = ((stateEnc & 0b11)<<2) | (dataB[i] & 0b11)  # calc. state from chA,chB 
          posEnc += luTable[stateEnc]         # increment current encoder position based on state
          sum = 2                         # 2 extra counts per 4 readings
          for j in range(4):     # find sum over most recent 4 time readings
              pi = (i-j) % ASIZE
              sum += dataT[pi]
          print("{0:6d},{1:8d}".format(posEnc,sum))
          i = (i+1) % ASIZE
          led1.toggle()           
# ---------------
main()
