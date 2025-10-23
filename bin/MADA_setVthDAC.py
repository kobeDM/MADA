#!/usr/bin/python3
import time
import argparse
import json
from udp_util import UDPGenericSocket
import MADA_defs as MADADef
import MADA_util as MADAUtil


def setVthDAC_run( maqs_sock_arr ):
    
    print( )
    print( "===========================" )
    print( " setVthDAC starting... " )
    print( "===========================" )
    MADAUtil.submit_to_all_maqs( maqs_sock_arr, MADADef.PACKET_SETVTHDAC )
    return


def setVthDAC_abort( ):
    print( )
    print( "===========================" )
    print( " setVthDAC aborting... " )
    print( "===========================" )
    # do nothing at this moment (under construction...)
    
    return

def main( ):
    print("** MADA_setVthDAC start from MAQS client **")
    print("** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **")
    print("** 2025 Aug by S. Higashino **")
    
    parser = argparse.ArgumentParser( )
    parser.add_argument( "-c", help = "config file name", default = MADADef.DEF_CONFIGFILE )
    args = parser.parse_args()

    mada_config_path = args.c
    MADAUtil.get_config( )
    with open( mada_config_path, "r" ) as config_open :
        config_load = json.load( config_open )

    # network connection 
    print( "Checking connection with MAQS servers..." )
    maqs_sock_arr = []
    for i in range( 6 ):
        maqs_name = f"MAQS{i+1}"
        maqs_IP = config_load[maqs_name]["IP"]
        maqs_port = config_load[maqs_name]["port"]
        maqs_sock = ( UDPGenericSocket( False, 1024 ), maqs_IP, (int)(maqs_port), maqs_name  )
        if maqs_sock[0].initialize( maqs_sock[1], maqs_sock[2] ) == False:
            print( "Connection error: failed to establish connection to " + maqs_sock[1] + "." )
            continue
        maqs_sock_arr.append( maqs_sock )
    if len( maqs_sock_arr ) < 1:
        print( "No MAQS servers connected. aborting..." )
        return
    print( )
    print( "MAQS servers connected.")
    print( )
        
    print( " === Distributing config file to all MAQS servers ===")
    MADAUtil.divide_config( config_load )
    print( " === Distributing config file Done ===")

    try:
        setVthDAC_run( maqs_sock_arr )
    except KeyboardInterrupt:
        setVthDAC_abort( )


    return    
    
if __name__ == "__main__":
    main( )
