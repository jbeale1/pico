# Measure elapsed time between rising edge on inputs A and B
# using only Python, not the PIO state machine
# Raspberry Pi Pico   J.Beale 7-March-2021

from machine import Pin  # for access to GPIO
import time  # for elapsed time

inA = Pin(16, Pin.IN, Pin.PULL_DOWN) # use this pin for input signal A
inB = Pin(17, Pin.IN, Pin.PULL_DOWN) # use this pin for input signal B
tus = time.ticks_us                  # 1 MHz timer object, tick = 1 microsecond

def main():
    tOld = getAB()
    while True:
      tInt = getAB()         # get an A->B pulse interval (in microseconds)
      tDelta = tInt - tOld   # find the change from last time
      print(tInt,",",tDelta) # current value, and change from previous
      tOld = tInt            # remember current value for next time

def getAB():     # measure interval between rising edges on A and B inputs
    waitA()           # wait for rising edge on input A
    tStart = tus()    # get timer for A edge
    waitB()           # wait for rising edge on B
    tEnd = tus()      # get timer for B edge
    tInterval = tEnd - tStart # find elapsed microseconds
    if (tInterval < 0):
        tInterval += 0x100000000  # 32-bit 1 MHz counter rolls over after 71.6 minutes
    return(tInterval)

def waitA():           # wait for rising edge on input A
  while inA.value():   # if input is high, wait for it to go low
      pass
  while not inA.value():  # now that it's low, wait for it to go high 
      pass

def waitB():           # wait for rising edge on input B
  while inB.value():  # if inB is high, wait for it to go low
      pass
  while not inB.value():  # wait for it to go high
      pass

# ----------------------------------------------------------------
main()
