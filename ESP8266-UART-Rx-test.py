# Slave device (ESP8266 board) main program
# https://forum.micropython.org/viewtopic.php?t=6182
# Silkscreen "RX" is UART0 Rx (pin 4, if 3V3 near FLASH button is pin 1)
# Also seems to go to the cp2102 USB-Serial chip, so be careful.

import machine
import uos
import utime

def main():
    recLines = []
    try:
        print("ESP8266-UART Receive Test starting...")
        uos.dupterm(None, 1) # disable REPL on UART(0)
    
        uart = machine.UART(0, rxbuf=64)                 
        uart.init(115200, timeout=100) # timeout in msec
        #uart.init(19200, timeout=100) # timeout in msec

        while True:
            if uart.any():
                hostMsg = uart.readline(64)
                if hostMsg is not None:                    
                    #strMsg = hostMsg.decode()
                    strMsg = hostMsg.decode().rstrip()
                    if strMsg == '\x00':
                        raise Exception
                    else:                        
                        recLines.append(strMsg)
                        # uart.write(strMsg + '\n')                                    
    except Exception:
        #uart.write('UART Exception was raised')
        pass
    finally:
        uos.dupterm(machine.UART(0, 115200), 1)
        utime.sleep(5) # allow time to remove signal on ESP UART Rx pin
        print("UART receive stopped.")
        for s in recLines:
            print("%s  len=%d" % (s,len(s)) )

# ============== Run main loop ===============
main()
