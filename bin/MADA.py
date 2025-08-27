#!/usr/bin/python3
import time
from udp_util import UDPGenericSocket
import MADA_defs as MADADef

socket_array = []
socket_array.append( ( UDPGenericSocket( False, 1024 ), '10.37.0.181', 9001  ) )
# socket_array.append( ( UDPGenericSocket( False, 1024 ), '10.37.0.182', 9002  ) )


def submit_to_maqs( message ):

    fail_submitting = False
    print("message submitting...")
    for socket in socket_array:
        if socket[0].send( message ) == False:
            print( "Connection error: failed to send message to " + socket[1] + ", aborting..." )
            fail_submitting = True

    return fail_submitting

# def check_maqs_status( ):

#     fail_submitting = False
#     print("check MAQS's status...")
#     for socket in socket_array:
#         if socket[0].send( message ) == False:
#             print( "Connection error: failed to send message to " + socket[1] + ", aborting..." )
#             fail_submitting = True

#     return fail_submitting

def daq_run( ):
    
    print( )
    print( "===========================" )
    print( " DAQ starting... " )
    print( "===========================" )
    
    while True:
        submit_to_maqs( MADADef.PACKET_DAQSTART )
        while True:
            submit_to_maqs( MADADef.PACKET_CHECKDAQ )
            time.sleep( 5 )
        
    return

def daq_abort( ):
    
    print( )
    print( "===========================" )
    print( " DAQ aborting... " )
    print( "===========================" )
    submit_to_maqs( MADADef.PACKET_DAQSTOP )
    
    return

def main( ):
    print("** MADA start from MAQS client **")
    print("** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **")
    print("** 2025 Aug by S. Higashino **")
    
    print( )
    print("Checking connection with MAQS's...")
    for socket in socket_array:
        if socket[0].initialize( socket[1], socket[2] ) == False:
            print( "Connection error: failed to establish connection to " + socket[1] + ", aborting..." )
            return

    print( )
    print("All MAQS's connected.")
    print( )
        
    try:
        daq_run( )
    except KeyboardInterrupt:
        daq_abort( )

    return    
    
if __name__ == "__main__":
    main( )
