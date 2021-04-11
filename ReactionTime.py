# Measure reaction time, from LED-on to switch closed, or IR beam blocked
# MicroPython v1.14 2021-03-12 on Raspberry Pi Pico with RP2040
# J.Beale 11-April-20211

from machine import Pin  # for access to GPIO
import urandom           # random numbers
import time              # for microseconds elapsed time

# ----------------------- a few global variables ---------------------

inA = Pin(16, Pin.IN, Pin.PULL_UP)   # input signal: switch to ground, or opto-interrupter
led = Pin(25, Pin.OUT)               # set pin 25 (driving onboard LED) to output

tus = time.ticks_us                  # 1 MHz timer object, tick = 1 microsecond
falseStart = 0                       # starting off with no mistakes
# --------------------------------------------------------------------------

def vBlink(p,t,n):      # blink LED on pin p, period 2*t milliseconds, repeat n times
    for i in range(n):
        p.value(1)      # bring pin high, on Pico that means LED on
        time.sleep_ms(t)
        p.value(0)      # LED off
        time.sleep_ms(t)

def earlyTrigger(ch):   # called when switch closed before LED goes on
    global falseStart
    falseStart += 1

def main():
    global inA
    vBlink(led,100,2)      # blinks for visual indication of startup
    
    now = time.localtime() # assumes host PC has updated it
    dt_string = ("%d-%02d-%02d %02d:%02d:%02d" % now[0:6])
    print("Reaction Time Test %s" % dt_string)

    totalTries = 10        # how many times to do the thing
    
    trial = 0
    lowest = 999           # our current fastest response time
    sum = 0
    unitWait = 10             # wait in units of this many msec
    oldStart = falseStart     # no false starts yet
    
    while trial < totalTries:
        trial += 1
        waitTime = urandom.randrange(2000,4000)  # wait in range of this many msec                
        inA.irq(trigger=Pin.IRQ_FALLING, handler=earlyTrigger)  # start interrupt handler
        loopCtr = waitTime / unitWait  # divide the wait into this many parts
        while loopCtr > 0:
            time.sleep_ms(unitWait)  # a short wait
            loopCtr -= 1
            if (falseStart > oldStart):  # has there been a false start?
              oldStart = falseStart
              vBlink(led,50,10)    # send out a set of blinks to complain
              debounce()           # don't chatter on the return edge

        # Now we have waited the full allotted time, start the test
        inA.irq(trigger=Pin.IRQ_FALLING, handler=None)  # disconnect interrupt callback

        tStart = tus()         # start time since LED on
        led.on()
        waitA_nEdge()          # wait for falling edge on input
        tEnd = tus()           # end time, after falling edge
        led.off()
        delay = time.ticks_diff(tEnd, tStart)  # total reaction time
        msec = delay / 1E3      # delay in units of milliseconds
        print("%2d  %d" % (trial,round(msec)))
        lowest = min(lowest, msec)
        sum += msec
        urandom.seed(delay)   # use variable delay to make the numbers actually random        
        debounce()
        
    vBlink(led,150,5)         # signal that we are now done
    average = (sum / trial)    
    print("Fastest time: %5.1f  Average: %5.1f  Errors: %d" % (lowest,average,falseStart))
    
# -----------------------------------------------

def waitA_nEdge():          # wait for falling edge on input A
    while not inA.value():  # if already low, wait for it to go high 
        pass
    while inA.value():      # now that it's high, wait for it to go low
        pass

def debounce():
    while not inA.value():  # if input still low, wait for it to go high 
        pass
    time.sleep_ms(100)  # then wait this much more for debouncing
# ----------------------------------------------------------------
main()
