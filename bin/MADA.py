#!/usr/bin/python3
import os
import sys
import time
from udp_util import UDPGenericSocket
import MADA_defs as MADADef
import MADA_util as MADAUtil


def submit_to_all_maqs( maqs_sock_arr, message ):
    submit_success = True
    print("message submitting to all maqs servers...")
    for maqs_sock in maqs_sock_arr:
        if submit_to_maqs( maqs_sock, message ) == False:
            submit_success = False
            
    return submit_success

def submit_to_maqs( maqs_sock, message ):
    submit_success = True
    print( f"message submitting to {maqs_sock[3]}...")
    if maqs_sock[0].send( message ) == False:
        print( "Connection error: failed to send message to " + maqs_sock[3] + ", aborting..." )
        submit_success = False

    return submit_success


def submit_to_macaron( message ):
    submit_success = True
    print("message submitting...")
    if macaron_sock[0].send( message ) == False:
        print( "Connection error: failed to send message to " + macaron_sock[3] + ", aborting..." )
        submit_success = False

    return submit_success

def submit_to_mascot( message ):
    submit_success = True
    print("message submitting...")
    if mascot_sock[0].send( message ) == False:
        print( "Connection error: failed to send message to " + mascot_sock[3] + ", aborting..." )
        submit_success = False

    return submit_success


def check_maqs_status( maqs_sock ):

    print("checking MAQS's status...")
    if submit_to_maqs( maqs_sock, MADADef.PACKET_CHECKDAQ ) == False:
        print( "Status check for " + maqs_sock[3] + " failed, aborting..." )
        return 
    
            




# def check_macaron_status( ):

#     fail_submitting = False
#     print("check MACARON's status...")

#     if maqs_sock[0].send( message ) == False:
#         print( "Connection error: failed to send message to " + maqs_sock[1] + ", aborting..." )
#         fail_submitting = True
#         return fail_submitting

#     reply_data = maqs_sock[0].receive( )
    
    
#     return fail_submitting


def daq_run( config_load, maqs_sock_arr, macaron_sock, mascot_sock ):

    # decide period number
    per_name = MADAUtil.make_new_period()
    cmd = f"mkdir {per_name}"
    proc = subprocess.run( cmd, shell = True )
    cmd = f"cp {mada_config_path} {per_name}"
    proc = subprocess.run( cmd, shell = True )

    datadir_name = config_load["general"]["datadir"]
    detector_name = config_load["general"]["detector"]
    current_dir_name = os.path.basename( os.getcwd( ) )
    for maqs_sock in maqs_sock_arr:
        maqs_name = maqs_sock[3]
        maqs_pername = f"{datadir_name}/{maqs_name}/{detector_name}/{current_dir_name}/{period}"
        if os.path.isdir( maqs_pername ) == True:
            print( f"period directory: {maqs_pername} already exists. aborting..." )
            sys.exit( 1 )
        cmd = f"mkdir {maqs_pername}"
        proc = subprocess.run( cmd, shell = True )
        
    print( )
    print( f"===========================" )
    print( f" DAQ starting... " )
    print( f" period : {per_name}" )
    print( f"===========================" )

    while True:

        # send software veto
        submit_to_macaron( MADADef.PACKET_SWVETO_ON )
        print( f"Activate software veto: command submitted to MACARON" )
        time.sleep( 1 )

        # send DAQ start flag to mascot
        submit_to_mascot( MADADef.PACKET_DAQSTART )
        print( f"LV auto-reset from SCSM is locked: command submitted to MASCOT" )
        time.sleep( 1 )
        
        # check LV status
        submit_to_mascot( MADADef.PACKET_LVCHECK )
        data = mascot_sock[0].receive( )
        if data == MADADef.PACKET_LVSTATUS_NG:
            print( f" === LV currents exceed threshold. LV reset start === " )
            print( )
            lv_reset_sleep = config_load["general"]["sleepLVReset"]
            submit_to_mascot( MADADef.PACKET_LVRESET )
            print( f"LV resetting... (sleep time: {lv_reset_sleep} sec.)" )
            time.sleep( lv_reset_sleep )
            while True:
                submit_to_mascot( MADADef.PACKET_LVCHECK )
                data = mascot_sock[0].receive( )
                if data == MADADef.PACKET_LVSTATUS_OK:
                    print( f"LV reset successfully done!" )
                    break
        print( )

        # configuration
        print( f"Vth and DAC parameter setting..." )
        submit_to_maqs( MADADef.PACKET_SETVTHDAC )
        while True:
            if MADAUtil.process_running( MADADef.PY_MAQS_SETVTHDAC ) == True:
                time.sleep( 1 )
                continue
            else:
                break
        print( f"Done!" )
            
        # DAQ start
        print( )
        print( )
        print( f" ===========================================================" )
        print( f" MAQS DAQ booting..." )
        print( f" ===========================================================" )
        print( )
        # submit_to_maqs( MADADef.PACKET_DAQSTART )
        while True:
            check_maqs_status( )
            
        # DAQ enable
        
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
    print( "** MADA start from MAMA **" )
    print( "** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **" )
    print( "** 2025 Aug by S. Higashino **" )

    parser = argparse.ArgumentParser( )
    parser.add_argument( "-c", help = "config file name", default = MADADef.DEF_CONFIGFILE )
    parser.add_argument( "-s", help = "silent mode (control only)", action = 'store_true' )
    parser.add_argument( "-n", help = "file size in MB", default = MADADef.DEF_FILESIZE )
    args = parser.parse_args()

    mada_config_path = args.c
    MADAUtil.get_config( )
    with open( mada_config_path, 'r' ) as config_open :
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
        daq_run( config_load, maqs_sock_arr, macaron_sock, mascot_sock )
        # submit_to_macaron( MADADef.PACKET_DAQENABLE )
        # time.sleep( 2 )
        # submit_to_macaron( MADADef.PACKET_DAQDISABLE )
    except KeyboardInterrupt:
        daq_abort( config_load, maqs_sock_arr, macaron_sock, mascot_sock )

    return    
    
if __name__ == "__main__":
    main( )
