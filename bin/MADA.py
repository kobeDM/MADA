#!/usr/bin/python3

from udp_util import UDPGenericSocket
import MADA_defs as MADADef

socket_array = []
socket_array.append( ( UDPGenericSocket( False, 1024 ), '10.37.0.181', 9001  ) )
# socket_array.append( ( UDPGenericSocket( False, 1024 ), '10.37.0.182', 9002  ) )

def main():

    print("** MADA start from MAQS client **")
    print("** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **")
    print("** 2025 Aug by S. Higashino **")
    
    print("")
    print("Checking connection with MAQS's...")
    for socket in socket_array:
        if socket[0].initialize( socket[1], socket[2] ) == False:
            print( "Connection error: failed to establish connection to " + socket[1] + ", aborting..." )
            return

    print("")
    print("All MAQS servers ready!!!")
    
    print("")
    print("DAQ starting...")
    for socket in socket_array:
        if socket[0].send( MADADef.MADA_PACKET_DAQSTART ) == False:
            print( "Connection error: failed to establish connection to " + socket[1] + ", aborting..." )
            return
    
    
if __name__ == "__main__":
    main( )
