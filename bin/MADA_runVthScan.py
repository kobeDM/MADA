#!/usr/bin/python3
import time
import argparse
import json
from udp_util import UDPGenericSocket
import MADA_defs as MADADef
import MADA_util as MADAUtil


def runVthScan_run( maqs_sock_arr, macaron_sock, mascot_sock ):
    
    print( )
    print( "===========================" )
    print( " runVthScan starting... " )
    print( "===========================" )

    # MACARON setting
    MADAUtil.submit_to_macaron( macaron_sock, MADADef.PACKET_SWVETO_ON )
    MADAUtil.submit_to_macaron( macaron_sock, MADADef.PACKET_TPMODE_ON )
    MADAUtil.submit_to_macaron( macaron_sock, MADADef.PACKET_DAQENABLE )
    MADAUtil.submit_to_macaron( macaron_sock, MADADef.PACKET_SWVETO_OFF )

    # submit runVthScan to MAQS
    MADAUtil.submit_to_all_maqs( maqs_sock_arr, MADADef.PACKET_VTHSCAN )
    time.sleep( 2 )
    
    # Status check
    while True:
        vth_scan_end = False
        for maqs_sock in maqs_sock_arr:
            if check_maqs_status( maqs_sock ) == MADADef.CTRL_MAQS_STATE_IDLE:
                print( f"VthScan finished." )
                vth_scan_end = True
                break
        if vth_scan_end == True:
            break
    
    # MACARON post process
    MADAUtil.submit_to_macaron( macaron_sock, MADADef.PACKET_DAQDISABLE )
    MADAUtil.submit_to_macaron( macaron_sock, MADADef.PACKET_TPMODE_OFF )

    return


def runVthScan_abort( ):
    
    print( )
    print( "===========================" )
    print( " runVthScan aborting... " )
    print( "===========================" )
    # do nothing at this moment (under construction...)
    
    return

def main( ):
    print("** MADA_runVthScan start from client **")
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
    print( "Checking connection with MACARON..." )
    macaron_IP = config_load["MACARON"]["IP"]
    macaron_port = config_load["MACARON"]["port"]
    macaron_sock = ( UDPGenericSocket( False, 1024 ), macaron_IP, (int)(macaron_port), "MACARON"  )
    if macaron_sock[0].initialize( macaron_sock[1], macaron_sock[2] ) == False:
        print( "Connection error: failed to establish connection to " + macaron_sock[1] + ", aborting..." )
        return
    print( )
    print( "MACARON connected." )

    print( )
    print( "Checking connection with MASCOT..." )
    mascot_IP = config_load["MASCOT"]["IP"]
    mascot_port = config_load["MASCOT"]["port"]
    mascot_sock = ( UDPGenericSocket( False, 1024 ), mascot_IP, (int)(mascot_port), "MASCOT"  )
    if mascot_sock[0].initialize( mascot_sock[1], mascot_sock[2] ) == False:
        print( "Connection error: failed to establish connection to " + mascot_sock[1] + ", aborting..." )
        return
    print( )
    print( "MASCOT connected." )
    
    print( )
    print( "Checking connection with MAQS servers..." )
    maqs_sock_arr = []
    for i in range( 6 ):
        maqs_name = f"MAQS{i+1}"
        maqs_IP = config_load[maqs_name]["IP"]
        maqs_port = config_load[maqs_name]["port"]
        maqs_sock = ( UDPGenericSocket( False, 1024 ), maqs_IP, (int)maqs_port, maqs_name  )
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
    
    try:
        runVthScan_run( maqs_sock_arr, macaron_sock, mascot_sock )
    except KeyboardInterrupt:
        runVthScan_abort( )


    return    
    
if __name__ == "__main__":
    main( )
