# Serial UART Rx to Net Socket data Tx, J.Beale March 16 2021
# ESP8266 receives data on UART and sends out via Wifi
# as network client, and expects remote server to be listening already.
#  (for example running 'nc -l <port>' on remote host)
# See: stackoverflow.com/questions/21233340/sending-string-via-socket-python

import machine        # hardware pins
import socket, errno  # NTP via wifi
import time      # RTC time/date stamp
import utime     # msec() and usec()
import uerrno    # list of symbolic OSError codes
import ntptime   # get current time of day
import uos       # disable REPL on uart
import network   # check on network status

# ----------------------------------------------------------------------
server = '192.168.1.105'  # remote server to send data (rp49.local)
port = 8889               # network port to communicate through

led = machine.Pin(2, machine.Pin.OUT)  # onboard LED
# ----------------------------------------------------------------------

def shortBlink():
     led.value(0)   # 0 means LED on
     time.sleep(0.15)
     led.value(1)
     time.sleep(0.15)

def longBlink():
     led.value(0)   # 0 means LED on
     time.sleep(0.4)
     led.value(1)
     time.sleep(0.4)

def startNet():                  # make sure we're online, check IP address
   wlan = network.WLAN(network.STA_IF) # create station interface
   while True:
     cFlag = wlan.isconnected()      # check if the station is connected to an AP
     if cFlag:                       # continue if so; loop if not
         break
     longBlink()    # slow blinks indicate WLAN not connected
     utime.sleep(2) # allow time to remove signal on ESP UART Rx pin
    
   config = wlan.ifconfig()  # get (IP, netmask, gateway, DNS)
   myIP = config[0]
   #print("My IP = %s" % myIP)
   for _ in range(2):  # fast blinks indicate successful connection
       shortBlink()   

def getTS():  # get a timestamp with current date & time
  t=time.localtime() #  wlan = network.WLAN(network.STA_IF)
  ts = '# START {:02d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}'.format(
    t[0], t[1], t[2], t[3], t[4], t[5])
  return(ts)

def openNet():  # open network port
 s = socket.socket()
 try:
    s.connect((server,port))
    return(s)
 except OSError as err:         # errno.ECONNRESET:    
    uos.dupterm(machine.UART(0, 115200), 1) # restore REPL
    utime.sleep(5) # allow time to remove signal on ESP UART Rx pin
    if err.args[0] == uerrno.ECONNRESET:
        longBlink()
        #print("Unable to connect to %s" % server)
    longBlink()
    #print("UART-Network test stopped.")
    utime.sleep(30)
    machine.reset()  # hard reset

# -----------------------------------------------------------
def main():

 ts = getTS()
 #print("%s" % ts)
 #print("ESP8266-UART Receive to Network Socket starting")
         
 #ntptime.settime()  # use network to set RTC to current time
 
 shortBlink()       # show NTP call returned
 ts = getTS()       # Date/Time string at program start
 #print("Current time: %s" % ts)
 #print("Y2K epoch： ", time.time() )
 #return  #  ======================== DEBUG
 
# -----------------------------------------------------
 try:
     stm = openNet()  # open network stream & send data 
     stm.send(("# Serial-Wifi Transfer v0.1 JPB 2021-03-17\n").encode())
     stm.send(("%s  Y2K epoch: %d\n" % (ts,time.time())).encode())
     # stm.send(("# Y2K epoch： %d\n" % time.time()).encode())
     utime.sleep_ms(50) 
     shortBlink()       # show Network call returned    
     # stm.close()
 except Exception:
     longBlink()
     utime.sleep(30)       # wait for awhile in case server comes back online
     stm.close()
     machine.reset()  # start over with hard reset
# ----------------------------------------------------- 
 
 
 # stm.close(); return   # ============  DEBUG  ============================
  
  
 time.sleep(2)
 uos.dupterm(None, 1) # disable REPL on UART(0), allowing ext. input
 uart = machine.UART(0, rxbuf=64)                 
 uart.init(115200, timeout=100) # timeout in msec

 pktNumber = 0

 while True:    # overall main loop, alternating UART Rx & Net Tx
     
    recLines = []  # list to hold input lines from UART
    try:
      loopCnt = 0
      while True:      # ======= loop to check for UART input =====
        if uart.any():        
          hostMsg = uart.readline(120)          
          if hostMsg is not None:
            rawMsg = hostMsg.decode().rstrip()
            if (loopCnt == 0):
              ts = getTS()     # get current timestamp on 1st line
            loopCnt += 1        
            strMsg = str(time.time()) + "," + rawMsg
            if rawMsg[0:6] == "**HALT":
                break  # end of serial input packet
            if rawMsg[0:6] == "**EXIT":
                uos.dupterm(machine.UART(0, 115200), 1) # restore local REPL
                utime.sleep_ms(500)
                return                
            else:                        
                recLines.append(strMsg)
        utime.sleep_ms(15)        
        if (loopCnt > 20000):  # <== TIMEOUT sets max duration packet (20k = 5 minutes)
          stm.close()  # close the port and quit.
          utime.sleep(60)  # don't reboot too quickly
          machine.reset()  # hard reset, like Reset button
          break
                
    except Exception as ex:
        stm.close()
        uos.dupterm(machine.UART(0, 115200), 1) # restore local REPL
        #utime.sleep(5) # allow time to remove signal on ESP UART Rx pin
        longBlink()
        #print("Exception: ", ex)
        #print("UART receive stopped, disconnect serial line")
        utime.sleep(5) # allow time to remove signal on ESP UART Rx pin
        #for s in recLines:
        #    print("%s  len=%d" % (s,len(s)) )
        #machine.soft_reset()  # stop. Micropython has no exit() as there is no OS    

# ---------------------------------------------------------------------
#   Done with UART, either error, timeout, or end of packet signal

    if (len(recLines) > 0):   # if there was any UART data received
     try:
      pktNumber += 1      
# ----------------------------------------------------- 
      # stm = openNet()  # open network stream & send data      
      stm.send((ts+'\n').encode())
      for outs in recLines:   # transmit each stored line
        outs1 = outs + '\n'  
        stm.send(outs1.encode())
      stm.send(("# END_PACKET %d\n" % pktNumber).encode())
      shortBlink()
      # utime.sleep_ms(20) 
      # stm.close()
# -----------------------------------------------------       
              
     except Exception as err:         # errno.ECONNRESET:
      stm.close()
      uos.dupterm(machine.UART(0, 115200), 1)
      #utime.sleep(5) # allow time to remove signal on ESP UART Rx pin
      
      if err.args[0] == uerrno.ECONNRESET:
        #print("Connection to %s reset by remote host." % server)
        longBlink()
      machine.soft_reset()  # stop. Micropython has no exit() as there is no OS
       
    #utime.sleep_ms(20)     
# ----- end of main ---------------------------------------------------

startNet()  # check we're online; wait if we aren't
main()

