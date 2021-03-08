# Code for Ball Incline Experiment #1
# Use optical interrupter to measure input velocity, exit velocity,
# and uphill roll time of ball going up slope through sensor,
# and ~ 1 second later returning back through sensor.
#
# MicroPython v1.14 on Raspberry Pi Pico   J.Beale 7-March-20211

from machine import Pin  # for access to GPIO
import time              # for microseconds elapsed time

diameter = 11.0;              # diameter of ball, in mm
dum = diameter * 1000;        # diameter of ball in microns

inA = Pin(16, Pin.IN, Pin.PULL_UP)   # use this pin for input signal
led = Pin(25, Pin.OUT)               # set pin 25 (driving onboard LED) to output

tus = time.ticks_us                  # 1 MHz timer object, tick = 1 microsecond
led.off()                            # make sure LED is off

def main():
    print("Ball Experiment Pulse Timer v1")
    print("n, rollTime (s), v1(m/s), v2(m/s), v1/t, v2/t, v12Ratio")
    waitA_p()                # A idles high so wait for A to go high, if it isn't already    
    progStart = tus()      # timer value as program starts
    rCnt = 0               # roll counter: how many rolls we have seen
    
    while True:
      pStartA1,ptime1 = getPulseA()  # start time and length of first pulse, in usec (ball going up)
      pStartA2,ptime2 = getPulseA()  # start time and length of second pulse, in usec (ball returning)
      rCnt += 1                      # count how many total ball excursions so far      
      v1 = dum / ptime1              # velocity1 (m/s) = distance (um) / time (us)
      v2 = dum / ptime2              # velocity2 (m/s)
      rT = (pStartA2 - (pStartA1+ptime1))/1E6   # time ball spends on uphill side of sensor (seconds)
      vRatio = v1 / v2              # ratio of start & end velocities
      print("%d,%8.6f,%5.3f,%5.3f,%5.3f,%5.3f,%5.3f" %
            (rCnt,rT,v1,v2,v1/rT,v2/rT,vRatio)) # calculated values for this ball cycle
# -----------------------------------------------

def rollFix(t):
    if (t < 0):
        t += 0x100000000  # 32-bit 1 MHz counter rolls over after 71.6 minutes
    return(t)

def getPulseA():           # measure input A positive pulse start time and pulse width
    waitA_nEdge()          # wait for rising edge on input A
    tStart = tus()         # get timer reading at rising edge
    led.on() 
    waitA_p()              # wait for A to go low again
    tEnd = tus()           # get timer reading on falling edge
    led.off() 
    tInterval = tEnd - tStart # find elapsed microseconds
    tInterval = rollFix(tInterval)         # fix for 32-bit rollover
    return(tStart,tInterval)

def waitA_nEdge():          # wait for falling edge on input A
    while not inA.value():  # if already low, wait for it to go high 
        pass
    while inA.value():      # now that it's high, wait for it to go low
        pass

def waitA_p():              # wait only so long as A remains low
    while not inA.value():  # and return immediately if A is already high
        pass

# ----------------------------------------------------------------
main()
