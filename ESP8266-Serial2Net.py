# ESP8266 Receives data on UART, and sends out via Wifi (network socket)
# as client. This presumes the remote server is listening already on the socket.
#  (eg. 'nc -l <port>' on remote host, but soon quits if output redirected?)
# See: stackoverflow.com/questions/21233340/sending-string-via-socket-python
#  J.Beale March 18 2021

import machine        # hardware pins
import socket, errno  # NTP via wifi
import time      # RTC time/date stamp
import utime     # msec() and usec()
import uerrno    # list of symbolic OSError codes
#import ntptime   # stock version fixed to pool.ntp.org
import uos       # disable REPL on uart
import network   # check on network status

# ----------------------------------------------------------------------
server = '192.168.1.105'    # remote server to send data (rp49.local)
port = 8889                 # network port to communicate through
NTP_host = '192.168.1.212'  # local NTP server with fixed IP address

led = machine.Pin(2, machine.Pin.OUT)  # onboard LED
# ----------------------------------------------------------------------

# Modified version of ntptime.py to use local NTP server
# https://github.com/micropython/micropython-infineon/blob/master/esp8266/scripts/ntptime.py
try:
    import ustruct as struct
except:
    import struct

# (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
NTP_DELTA = 3155673600

def NTP_time(nhost):
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1b
    #addr = socket.getaddrinfo(NTP_host, 123)[0][-1]
    #print(addr) # DEBUG!!
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1)
    res = s.sendto(NTP_QUERY, (nhost, 123))
    msg = s.recv(48)
    s.close()
    val = struct.unpack("!I", msg[40:44])[0]
    return val - NTP_DELTA

# --------------------------------------------------------

# There's currently no timezone support in MicroPython, so
# utime.localtime() will return UTC time (as if it was .gmtime())
def NTP_settime(nhost):
    t = NTP_time(nhost)
    import machine
    import utime
    tm = utime.localtime(t)
    tm = tm[0:3] + (0,) + tm[3:6] + (0,)
    machine.RTC().datetime(tm)
    #print(utime.localtime())
# -------------------------------------------------------
def vBlink(t):      # variable-length blink of duration t seconds
     led.value(0)   # 0 means LED on
     time.sleep(t)
     led.value(1)
     time.sleep(t)

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

 NTP_settime(NTP_host)   # custom version set to my server 
 
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
 shortBlink()       # show Network call returned    

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
          longBlink()
          longBlink()
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

    vBlink(0.1)
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
      vBlink(0.1)
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
