# From https://www.raspberrypi.org/forums/viewtopic.php?p=1842706#p1842706
# Author: RPi Forum user 'horuable'
# Mods: J.Beale 26-March-2021

from machine import Pin, mem32
from rp2 import asm_pio, StateMachine, PIO
from time import ticks_ms, ticks_diff
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
    
    wrap_target()
    label("loop")
    mov(x, 10) .side(1) # 10 seems to work, 0 does not... (why?)
    wait(0, pin, 2)
    in_(pins, 2)
    push()
    label("counter_start")
    jmp(pin, "output")
    jmp(x_dec, "counter_start")
    label("output")
    mov(isr, invert(x)) .side(0)
    push()
    jmp(y_dec, "loop")
    irq(noblock, 0x10)   # 'block' works, but more timing cycles get lost
    mov(y, 3) .side(0)
    wrap()

data = array.array("I", [0]*8)
start = ticks_ms()
def counter_handler(sm):
    global start
    for i in range(8):
        data[i] = sm.get()
    tSum = (data[1]+data[3]+data[5]+data[7])  # - 499998xx
    tNow = ticks_ms()
    tDelta = ticks_diff(tNow, start) # input signal period, milliseconds
    print("%d,%d,%d,%d,%d,%d" % (tDelta,data[0],data[2],data[4],data[6],tSum))
    start = tNow

"""
# Instantiate and configure signal simulating SMs
sm0 = StateMachine(0, in_sig_sim, freq=1_000_000, set_base=Pin(14))
sm0.put(500_000) # Frequency control
sm0.exec("pull()")
sm0.exec("mov(isr, osr)")
sm0.put(100_000) # Delay control
sm0.exec("pull()")
sm0.exec("mov(x, osr)")
sm1 = StateMachine(1, in_sig_sim, freq=1_000_000, set_base=Pin(15))
sm1.put(500_000) # Frequency control
sm1.exec("pull()")
sm1.exec("mov(isr, osr)")
sm1.put(1) # Delay control
sm1.exec("pull()")
sm1.exec("mov(x, osr)")
"""

chA = Pin(14,Pin.IN,Pin.PULL_UP)  # encoder A input signal
chB = Pin(15,Pin.IN,Pin.PULL_UP)  # encoder B input signal
chFlag = Pin(16)  # Flag signal, goes high for 2 cycles when chA or chB edge detected

sm2 = StateMachine(2, trigger, freq=100_000_000, in_base=chA, set_base = chFlag)
sm2.active(1)
sm3 = StateMachine(3, trigger, freq=100_000_000, in_base=chB, set_base = chFlag)
sm3.active(1)

sm4 = StateMachine(4, counter, freq=100_000_000, in_base=chA, jmp_pin = chFlag, sideset_base=Pin(25))
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

# Note: all output is generated after Python REPL prompt returns (!)
