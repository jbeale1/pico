# From https://www.raspberrypi.org/forums/viewtopic.php?p=1842706#p1842706
# Author: RPi Forum user 'horuable'
# Mods: J.Beale 26-March-2021

from machine import Pin, mem32
from rp2 import asm_pio, StateMachine, PIO
from time import ticks_ms, ticks_us, ticks_diff, sleep
import array

# Simulation SM
@asm_pio(set_init=PIO.OUT_LOW)
def in_sig_sim():
    label("delay")
    jmp(x_dec, "delay")
    wrap_target()
    set(pins, 0)
    mov(y, isr)
    label("low")
    jmp(y_dec, "low")
    set(pins, 1)
    mov(y, isr)
    label("high")
    jmp(y_dec, "high")
    wrap()

# generate a 2-cycle flag signal after each input edge
@asm_pio(set_init=PIO.OUT_HIGH)  
def trigger():
    wait(1, pin, 0)
    set(pins, 1) [2]
    set(pins, 0)
    wait(0, pin, 0)
    set(pins, 1) [2]
    set(pins, 0)

@asm_pio(sideset_init=PIO.OUT_LOW)
def counter():
    mov(y, 3)       # 4 passes for the 4 edges of quadrature signal
    wait(1, pin, 2)
    
    wrap_target()       # -- top of main r (run-forever) loop
    label("loop")       # --- top of inner 4-cycle loop
    mov(x, 10) .side(0) # 10 seems to work, 0 does not... (why?)
    wait(0, pin, 2)
    in_(pins, 2)
    push()
    label("counter_start")
    jmp(pin, "output")
    jmp(x_dec, "counter_start")
    label("output")
    mov(isr, invert(x)) .side(1)
    push()
    jmp(y_dec, "loop")   # --- end of inner 4-cycle loop
    
    irq(noblock, 0x10)   # signal 8 words of data are now read to read
    mov(y, 3) .side(0)
    wrap()               # ----- outer run-forever loop

def counter_handler(sm):
    global start
    global stateEnc
    global posEnc
    global luTable   # encoder output lookup table
    global led1
    data = array.array("I", [0]*8)
    tickSum = 0
    for i in range(4):
        stateEnc = ((stateEnc&0b11)<<2) | (sm.get() & 0b11)  # read chA,chB & calc. state
        posEnc += luTable[stateEnc]         # increment current encoder position based on state
        tickSum += sm.get()  # add up total elapsed time        
    tNow = ticks_us()
    tDelta = ticks_diff(tNow, start) # input signal period, milliseconds
    print("%d,%d,%d" % (tDelta,posEnc,tickSum))
    start = tNow
    led1.toggle()
    
# --------------------------------------------
def main():
  global start
  global stateEnc
  global posEnc
  global luTable   # encoder output lookup table
  global led1

  led1 = Pin(25, Pin.OUT)
  led1.off()

  posEnc=0
  stateEnc=0
  luTable = [0,-1,+1, 0,+1, 0, 0,-1,-1, 0, 0,  +1,  0, +1, -1,  0]  # for both pins P1,P2
  start = ticks_us()

  chA = Pin(14,Pin.IN,Pin.PULL_UP)  # encoder A input signal
  chB = Pin(15,Pin.IN,Pin.PULL_UP)  # encoder B input signal
  chFlag = Pin(16)  # Flag signal, goes high for 2 cycles when chA or chB edge detected

  sm2 = StateMachine(2, trigger, freq=100_000_000, in_base=chA, set_base = chFlag)
  sm2.active(1)
  sm3 = StateMachine(3, trigger, freq=100_000_000, in_base=chB, set_base = chFlag)
  sm3.active(1)

  sm4 = StateMachine(4, counter, freq=100_000_000, in_base=chA, jmp_pin = chFlag, sideset_base=Pin(22))
  sm4.irq(counter_handler)

  PIO0_BASE = 0x50200000
  PIO1_BASE = 0x50300000
  PIO_CTRL =  0x000
  SM0_EXECCTRL = 0x0cc
  SM0_SHIFTCTRL = 0x0d0
  # Join output FIFOs for sm4
  mem32[PIO1_BASE | SM0_SHIFTCTRL + 0x1000] = 1<<31
  sm4.active(1)
  # Start sm0 and sm1 in sync
  # mem32[PIO0_BASE | PIO_CTRL + 0x1000] = 0b11

  while True:  # all the action is in the interrupt routine
      sleep(1)
      
# ---------------
main()
