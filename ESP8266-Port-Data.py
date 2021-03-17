# Socket data transfer Tx/Rx, J.Beale March 16 2021
# ESP8266 device is client, and expects remote server to be listening already.
# for example running 'nc -l 8888' on remote host

# https://stackoverflow.com/questions/21233340/sending-string-via-socket-python

import socket, errno, time, machine, utime
import uerrno  # list of symbolic OSError codes

server = '192.168.1.105'  # remote server to send data (rp49.local)
s = socket.socket()
try:
    s.connect((server,8888))  

except OSError as err:         # errno.ECONNRESET:
    if err.args[0] == uerrno.ECONNRESET:
        print("Unable to connect to %s" % server)
    machine.soft_reset()  # halt and catch fire. Well, not really.
    
while True:
    try:
      for i in range(10):  # just send out a bunch of time data, as strings
        outs = str(utime.ticks_ms()) + ", " + str(utime.ticks_us()) + '\n'
        s.send(outs.encode())
    except OSError as err:         # errno.ECONNRESET:
      if err.args[0] == uerrno.ECONNRESET:
        print("Connection to %s reset by remote host." % server)
      machine.soft_reset()  # stop. Micropython has no exit() as there is no OS
       
    # print("Reply: ",s.recv(1024).decode())  # get reply data from host
    time.sleep(2)
    
s.close()
