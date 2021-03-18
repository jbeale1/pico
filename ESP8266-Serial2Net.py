# Socket data transfer Tx/Rx, J.Beale March 16 2021
# ESP8266 receives data on UART and sends out via Wifi
# as network client, and expects remote server to be listening already.
#  (for example running 'nc -l <port>' on remote host)

# https://stackoverflow.com/questions/21233340/sending-string-via-socket-python

import machine        # hardware pins
import socket, errno  # NTP via wifi
import time      # RTC time/date stamp
import utime     # msec() and usec()
import uerrno    # list of symbolic OSError codes
import ntptime   # get current time of day
import uos       # disable REPL on uart

# ----------------------------------------------------------------------
server = '192.168.1.105'  # remote server to send data (rp49.local)
port = 8889               # network port to communicate through
# ----------------------------------------------------------------------

def getTS():  # get a timestamp with current date & time
  t=time.localtime() #  
  ts = '{:02d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}'.format(
    t[0], t[1], t[2], t[3], t[4], t[5])
  return(ts)

def openNet():
 s = socket.socket()
 try:
    s.connect((server,port))
    # === Here, we have opened a network connection
    return(s)
 except OSError as err:         # errno.ECONNRESET:    
    uos.dupterm(machine.UART(0, 115200), 1) # restore REPL
    utime.sleep(5) # allow time to remove signal on ESP UART Rx pin
    if err.args[0] == uerrno.ECONNRESET:
        print("Unable to connect to %s" % server)
    print("UART-Network test stopped.")            
    machine.soft_reset()  # 

def main():

 ts = getTS()
 print("Time: %s" % ts)
 print("ESP8266-UART Receive to Network Socket starting")
         
 ntptime.settime()  # use network to set RTC to current time
 
 ts = getTS()  # starting Date/Time string
 print("UTC time: %s" % ts)
 print("Y2K epoch： ", time.time() )
 
# ----------------------------------------------------- 
 stm = openNet()  # open network stream & send data 
 stm.send(("Serial-Wifi Transfer v0.1 JPB 2021-03-17\n").encode())
 stm.send(("UTC time: %s   " % ts).encode())
 stm.send(("Y2K epoch： %d\n" % time.time()).encode())
 utime.sleep_ms(50) 
 stm.close()
# ----------------------------------------------------- 
 

# ==================== DEBUG ======================
 time.sleep(5)
 uos.dupterm(None, 1) # disable REPL on UART(0), allowing ext. input
 uart = machine.UART(0, rxbuf=64)                 
 uart.init(115200, timeout=100) # timeout in msec

 pktNumber = 0

 while True:
    recLines = []  # list to hold input lines from UART

    try:
      #print("ESP8266-UART Receive Test starting...")
      loopCnt = 0
      while True:
        if uart.any():
        #if True:    # DEBUG
          hostMsg = uart.readline(64)
          #hostMsg = ("test %d" % loopCnt).encode('utf8')  # DEBUG
          if hostMsg is not None:
            rawMsg = hostMsg.decode().rstrip()
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
        loopCnt += 1        
        if (loopCnt > 2000):  # <== TIMEOUT sets max duration packet
          break
                
    except Exception as ex:
        uos.dupterm(machine.UART(0, 115200), 1) # restore local REPL
        utime.sleep(5) # allow time to remove signal on ESP UART Rx pin
        print("Exception: ", ex)
        print("UART receive stopped, disconnect serial line")
        utime.sleep(5) # allow time to remove signal on ESP UART Rx pin
        for s in recLines:
            print("%s  len=%d" % (s,len(s)) )
        #machine.soft_reset()  # stop. Micropython has no exit() as there is no OS    

# ---------------------------------------------------------------------

    if (len(recLines) > 0):   # if there was any UART data received
     try:
      pktNumber += 1      
# ----------------------------------------------------- 
      stm = openNet()  # open network stream & send data
      stm.send((ts+'\n').encode())
      for outs in recLines:   # transmit each stored line
        outs1 = outs + '\n'  
        stm.send(outs1.encode())
      stm.send(("End of packet %d\n\n" % pktNumber).encode())
      utime.sleep_ms(20) 
      stm.close()
# -----------------------------------------------------       
              
     #except OSError as err:         # errno.ECONNRESET:              
     except Exception as err:         # errno.ECONNRESET:
      uos.dupterm(machine.UART(0, 115200), 1)
      #utime.sleep(5) # allow time to remove signal on ESP UART Rx pin
      
      if err.args[0] == uerrno.ECONNRESET:
        print("Connection to %s reset by remote host." % server)
      machine.soft_reset()  # stop. Micropython has no exit() as there is no OS
       
    utime.sleep_ms(20)     
# ----- end of main ---------------------------------------------------

main()
