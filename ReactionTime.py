# Measure reaction time, from LED-on to beam-blocked
# MicroPython v1.14 on Raspberry Pi Pico   J.Beale 11-April-20211

from machine import Pin  # for access to GPIO
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
    vBlink(led,50,10)    # warning blink when premature trigger
    time.sleep_ms(1000)  # extra wait time


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
    while trial < totalTries:
        trial += 1
        waitTime = urandom.randrange(2000,5000)  # wait in range of this many msec
        inA.irq(trigger=Pin.IRQ_FALLING, handler=earlyTrigger)  # start interrupt handler
        time.sleep_ms(waitTime)
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
