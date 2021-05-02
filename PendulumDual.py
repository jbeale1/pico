# Track position of pendulum flag with dual sensors
# ChA low when pendulum @ left, ChB low with pendulum @ right
# MicroPython for Raspberry Pi Pico (RP2040)
# J.Beale 28-APR-2021

"""    GP## numbering as per RasPi Pico pinout on p.4 of
https://datasheets.raspberrypi.org/pico/pico-datasheet.pdf
"""

import sys
from machine import Pin, mem32
from rp2 import asm_pio, StateMachine, PIO
from time import ticks_ms, ticks_us, ticks_diff, sleep, sleep_ms, sleep_us, localtime, time
import array
import math   # for sqrt in standard deviation

MFREQ = 200_000_000  # CPU frequency in Hz (typ. 125 MHz; Overclock to 250 MHz)
VERSION = "Pendulum v2.1 28-APR-2021 J.Beale"

# -----------------------------------------
def vBlink(p,t,n):      # blink LED on pin p, duration t milliseconds, repeat n times
    for i in range(n):
        p.value(1)
        sleep_ms(t)
        p.value(0)      # Pico, ESP32: 0 means LED off
        sleep_ms(t)
# -----------------------------------------
def variance(data, ddof=1):  # ddof: 0=population, 1=sample
    n = len(data)
    mean = sum(data) / n
    return (mean,sum((x - mean) ** 2 for x in data) / (n - ddof))

def stdev(data):
    m,var = variance(data)
    std_dev = math.sqrt(var)
    return m,std_dev


def driveStart():   # start pendulum swinging from standstill
    out1 = Pin(2, Pin.OUT)  # output to drive coil
    out1.off()
    
    pPeriod = int(1013807.708)   # pendulum period in microseconds
    qPeriod = int(pPeriod/4)     # time for 1/4 of a full swing
    cycles = 80  # 100: v=0.027751   80: 0.026835
    while cycles > 0:
        out1.on()
        sleep_us(qPeriod)
        out1.off()
        sleep_us(3*qPeriod)
        cycles -= 1

# --------------------------------------------------------------

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

ASIZE = 1023                         # size of circular data buffers (dataT, dataB)
dataT = array.array("I", [0]*ASIZE)  # store UINT32 timing data
dataB = array.array("B", [0]*ASIZE)  # store UCHAR bits (Ch.A, Ch.B values)
dIdx = 0                         # curent index into DATA array
bufT = array.array("I", [0]*4)      # last 4 values of timer data
bufC = array.array("I", [0]*4)      # count of last four sets (full-swing groups)


def counter_handler(sm):
    global dIdx
    dataB[dIdx] = sm.get() & 0b11    # read chA,chB
    dataT[dIdx] = sm.get() + 4       # read timer value
    dIdx = (dIdx + 1) % ASIZE        # increment index in circular buffer
    
# --------------------------------------------
def main():
  global start
  global stateEnc
  global posEnc
  global luTable   # encoder output lookup table
  global led1
  global dIdx      # index into data buffers, updated in interrupt routine
  
  gSize = 20       # group sample size for std.dev calculation
  deltaA = array.array("f", [0]*gSize)  # store float time ratios
  #deltaA = array.array("l", [0]*gSize)  # store INT32 timing deltas
  f = 0.1          # low-pass filter constant

  machine.freq(MFREQ)
  led1 = Pin(25, Pin.OUT)
  led1.off()
  out1 = Pin(2, Pin.OUT)  # output to drive coil
  out1.off()

  vBlink(led1,100,4)  # 4 short, 4 long blinks to indicate program start
  sleep_ms(500)
  vBlink(led1,200,4)
  #sleep_ms(4000)  # delay allows starting recording program
      
  # write CSV header line

  tStart = time() # assumes host PC has updated it
  now = localtime(tStart)
  dt_string = ("%d-%02d-%02d %02d:%02d:%02d" % now[0:6])  
    
  print("msec,t00,t10,t20,t11,diff,sum")
  print("# Start: %s  %s" % (dt_string,VERSION))
    
  posEnc= 0
  stateEnc = 0  # 4-bit encoder state (P2old,P1old,P2new,P1new)
  luTable = [0,-1,+1, 0,+1, 0, 0,-1,-1, 0, 0,  +1,  0, +1, -1,  0]  # for both pins P1,P2
  start = ticks_us()
  start_ms = ticks_ms()

  chA = Pin(16,Pin.IN,Pin.PULL_UP)  # encoder A input signal
  chB = Pin(17,Pin.IN,Pin.PULL_UP)  # encoder B input signal
  chFlag = Pin(18)  # Flag signal, goes high for 2 cycles when chA or chB edge detected

  #smf = int(MFREQ/10)  # was 200M
  smf = int(MFREQ/1)  # was 200M
  sm2 = StateMachine(2, trigger, freq=smf, in_base=chA, set_base = chFlag)  # watch Ch.A
  sm2.active(1)
  sm3 = StateMachine(3, trigger, freq=smf, in_base=chB, set_base = chFlag)  # watch Ch.B
  sm3.active(1)
                   # count time between edges on both Ch.A and Ch.B
  sm4 = StateMachine(4, counter, freq=smf, in_base=chA, jmp_pin = chFlag, sideset_base=Pin(22))
  sm4.irq(counter_handler)

  sm4.active(1)

  flagWidth = 5.0 * 1E-3   # width of interrupter flag, in meters
  countsPerSec = smf / 2   # count rate is 1/2 of state machine frequency
  # print("Counts per sec = %d" % countsPerSec)
  aHigh = 0;  aLow = 0
  aHighOld = 0; aLowOld = 0
  skip = False       # True to skip one half-swing to align drive phase
  # durStart = 21000   # initial microseconds duration of drive pulse
  durStart = 15_000   # initial microseconds duration of drive pulse
  durMax =  250_000    # maximum allowed drive period
  v1Setpoint = 0.025 # target velocity (m/s)
  intTerm = 0        # integral term correction of drive output
  kp = 4E7           # proportional control constant (was kp,ki: 2E7,5E4)
  ki = 5E4           # integral control constant
  f = 0.1            # low-pass filter constant
  
  rCount = 0  # total number of reading pairs received
  i = 0  # starting index into data arrays
  j = 0  # index into deltaA[]
  k = 0  # index into bufC[]
  aSum = 0  # how many counts in a full swing
  dcF = 0   # low-pass filtered difference

  #sys.exit()  # DEBUG
  # driveStart()  # get pendulum swinging enough to read position output

  while True:                 # get the first 4 readings, both high & low
      if (dIdx != i):  # any new data in the buffer?
        flag = ~(dataB[i]) & 0x03 # in binary: 10 @ left, 01 @ right
        # print("{0:02b}".format(flag),end=", ")
        if (dataB[i] & 0x01):   # is input A high or low level now?
            aHigh = dataT[i]
            aLowOld = aLow
        else:
            aLow = dataT[i]
            aHighOld = aHigh
        i = (i+1) % ASIZE
        if (aHighOld > 0) and (aLowOld > 0):
            aSumOld = aHigh + aLow
            v1 = flagWidth / (aLow / countsPerSec)  # velocity = distance / time
            v2 = v1
            vErrorOld = ((v1+v2)/2) - v1Setpoint
            dV1f = 0
            dV2f = 0
            v1Old = v1; v2Old = v2  # remember previous velocity
            if (flag == 0x01):
              break

  eCount = 0 # event counter
  while True:  # all the action is in the interrupt routine
      if (dIdx != i):  # any new data in the buffer?
          flag = ~(dataB[i]) & 0x03 # in binary: 10 @ left, 01 @ right
          #print("{0:02b}".format(flag),end=", ")
          tval = dataT[i]
          aSum += tval
          bufT[eCount%4] = tval
          eCount += 1
          #print("%d" % tval,end=", ")  # timer value
          if (flag == 0x01):
            diffCnt = bufT[1]-bufT[3]
            dcF = (1.0-f)*dcF + f*diffCnt
            bufC[k] = eCount
            k += 1
            if (k > 3):
                k = 0
                
            # only print out data when we've had 4 sets each with exactly 4 values
            # so we don't print when swing is too high, with extra edges from overshoot
            if (bufC[0]==4) and (bufC[1]==4) and (bufC[2]==4) and (bufC[3]==4):
              #print("bT3:%d, %d, %d" % (bufT[3],diffCnt,aSum)) # difference, total counts
              elapsed_ms = ticks_diff(ticks_ms(),start_ms)
              print("%d,%d,%d,%d,%d"%(elapsed_ms,bufT[0],bufT[1],bufT[2],bufT[3]),end=",")
              print(" %d, %d" % (dcF,aSum)) # difference, total counts
              #print("%d" % aSum)  # total counts this pendulum cycle
            else:
              start_ms = ticks_ms()  # reset start time for next cycle


            """
            if eCount != 4:   # abnormal count: amplitude has decayed too far; end run
                tEnd = time() # assumes host PC has updated it
                now = localtime(tEnd)
                tDur = (tEnd - tStart)
                dt_string = ("%d-%02d-%02d %02d:%02d:%02d" % now[0:6])  
                print("# End: %s  Duration: %d" % (dt_string, tDur))
                sys.exit()
            """
            aSum = 0
            eCount = 0
          """
          if (dataB[i] & 0x01):   # is input A high or low level now?
              aHigh = dataT[i]
          else:
              rCount += 1
              aLow = dataT[i]
              aSum = aHigh + aLow
              v1 = flagWidth / (aLow / countsPerSec)  # velocity = distance / time
              v2 = flagWidth / (aLowOld / countsPerSec)  # velocity = distance / time
              #cOffset = 24_012_094
              cOffset = 0
              aRatio = aSum / aSumOld  # difference in clock ticks between alternate half-swings
              if (rCount % 2) == 0:
                  msNow = ticks_diff(ticks_ms(),start_ms)
                  dV1 = (v1 - v1Old)*1E6  # change in velocity from previous cycle
                  dV2 = (v2 - v2Old)*1E6
                  dV1f = dV1f * (1.0-f) + (f * dV1)  # low-pass filtered version of dV1
                  dV2f = dV2f * (1.0-f) + (f * dV2)  # low-pass filtered version of dV1
                  led1.toggle()
                  out1.on()
                  vError = ((v1+v2)/2) - v1Setpoint
                  dvError = (vError - vErrorOld)*1E3
                  vErrorOld = vError
                  intTerm += int(vError * ki)  # integral control
                  driveDur = durStart - int(vError * kp) - intTerm
                  if driveDur > durMax:
                      driveDur = durMax
                  
                  if driveDur < 0:
                      driveDur = 0
                  sleep_us(driveDur) # @ v1=.0234, 25:+8u, 0:-20u (per cycle)
                                     # @ v1=.0284, 20:-4u, 0:-22u
                  out1.off()
                  # if (v1 < 0.1) and (v1 > 0.05):
                  if True:                      
                    print("%d," % msNow,end="")
                    print("{0:8d},{1:8.6f},{2:9.6f},{3:9.6f},{4:d},{5:5.3f},{6:d}"
                          .format(aSum,aRatio,v1,v2,intTerm,dvError,driveDur),end="")
                    print()
                  else:
                    start_ms = ticks_ms()
                  deltaA[j] = aRatio       # store in array for stdev calc
                  v1Old = v1; v2Old = v2  # remember previous velocity
                  #j += 1
                  #if (j==gSize):
                  #    mean,sdev = stdev(deltaA)
                  #    print(", {0:8.0f}, {1:6.3f}".format(mean,sdev))
                  #    j = 0
                  #else:
                  #    print()
                  
              aHighOld = aHigh
              aLowOld = aLow
              aSumOld = aSum
          """
          i = (i+1) % ASIZE

# ---------------
main()
