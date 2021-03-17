# Socket data transfer Tx/Rx, J.Beale March 16 2021
# ESP8266 device is client, and expects remote server to be listening already.
# for example running 'nc -l <port>' on remote host

# https://stackoverflow.com/questions/21233340/sending-string-via-socket-python

import machine        # hardware pins
import socket, errno  # NTP via wifi
import time    # RTC time/date stamp
import utime   # msec() and usec()
import uerrno  # list of symbolic OSError codes
import ntptime # get current time of day

server = '192.168.1.105'  # remote server to send data (rp49.local)
port = 8889

ntptime.settime()
print("UTC time：%s" % str(time.localtime())) # UTC time after sync
print("UTC epoch： ", time.time() )

s = socket.socket()
try:
    s.connect((server,port))  

except OSError as err:         # errno.ECONNRESET:
    if err.args[0] == uerrno.ECONNRESET:
        print("Unable to connect to %s" % server)
    machine.soft_reset()  # 
    
pktNumber = 0
while True:
    try:
      pktNumber += 1
      ts = str(time.localtime())
      print("%s Packet %d" % (ts,pktNumber))
      s.send((ts+'\n').encode())
      for i in range(10):  # just send out a bunch of time data, as strings
        outs = str(utime.ticks_ms()) + ", " + str(utime.ticks_us()) + '\n'
        s.send(outs.encode())
      s.send(("End of packet %d\n\n" % pktNumber).encode())
        
    except OSError as err:         # errno.ECONNRESET:
      if err.args[0] == uerrno.ECONNRESET:
        print("Connection to %s reset by remote host." % server)
      machine.soft_reset()  # stop. Micropython has no exit() as there is no OS
       
    # print("Reply: ",s.recv(1024).decode())  # get reply data from host
    time.sleep(2)
    
s.close()

"""
Sample output on remote server:

(2021, 3, 17, 17, 24, 10, 2, 76)
3894232, 673010544
3894240, 673017932
3894247, 673025313
3894255, 673032696
...and so forth

"""
