# Measure reaction time, from LED-on to beam-blocked
# MicroPython v1.14 on Raspberry Pi Pico   J.Beale 11-April-20211

from machine import Pin  # for access to GPIO
from machine import enable_irq, disable_irq  # inside long interrupt routine 
import urandom           # random numbers
import time              # for microseconds elapsed time

inA = Pin(16, Pin.IN, Pin.PULL_UP)   # use this pin for input signal
led = Pin(25, Pin.OUT)               # set pin 25 (driving onboard LED) to output

tus = time.ticks_us                  # 1 MHz timer object, tick = 1 microsecond
led.off()                            # make sure onboard LED is off
falseStart = 0                       # start off with no mistakes

def vBlink(p,t,n):      # blink LED on pin p, duration t milliseconds, repeat n times
    for i in range(n):
        p.value(1)
        time.sleep_ms(t)
        p.value(0)      # Pico, ESP32: 0 means LED off
        time.sleep_ms(t)

def earlyTrigger(ch):
    global falseStart
    falseStart += 1

def main():
    global inA
    vBlink(led,100,2)
    now = time.localtime()
    dt_string = ("%d-%02d-%02d %02d:%02d:%02d" % now[0:6])
    print("Reaction Time Test %s" % dt_string)

    totalTries = 10
    trial = 0
    lowest = 999
    sum = 0
    unitWait = 10             # wait in units of this many msec
    oldStart = falseStart     # no false starts yet
    while trial < totalTries:
        trial += 1
        waitTime = urandom.randrange(2000,4000)  # wait in range of this many msec
        inA.irq(trigger=Pin.IRQ_FALLING, handler=earlyTrigger)  # start interrupt handler
        loopCtr = waitTime / unitWait
        while loopCtr > 0:
            time.sleep_ms(unitWait)  # a short wait
            loopCtr -= 1
            if (falseStart > oldStart):  # did we just have a false start?
              oldStart = falseStart
              vBlink(led,50,10)    # warning blink when premature trigger           
              while not inA.value():  # if still low, wait for it to go high 
                  pass

        # here, we have waited for the alloted time, so start the test
        inA.irq(trigger=Pin.IRQ_FALLING, handler=None)  # disable interrupt handler

        tStart = tus()         # start time since LED on
        led.on()
        waitA_nEdge()          # wait for falling edge on input
        tEnd = tus()           # end time, after falling edge
        led.off()
        delay = time.ticks_diff(tEnd, tStart)  # total reaction time
        sec = delay / 1E6      # delay in units of seconds
        print("%d  %5.3f" % (trial,sec))
        lowest = min(lowest, sec)
        sum += sec
        urandom.seed(delay)   # use variable delay to make the numbers actually random
        while not inA.value():  # if still low, wait for it to go high 
          pass
        time.sleep_ms(100)    # debouncing wait
        
    vBlink(led,150,5)         # signal that we are now done
    average = (sum / trial)    
    print("Fastest time: %5.4f  Average: %5.4f  Errors: %d" % (lowest,average,falseStart))
    
# -----------------------------------------------

def waitA_nEdge():          # wait for falling edge on input A
    while not inA.value():  # if already low, wait for it to go high 
        pass
    while inA.value():      # now that it's high, wait for it to go low
        pass

# ----------------------------------------------------------------
main()
