#!/usr/bin/python3
import os
import sys
import time
import argparse
import json
from udp_util import UDPGenericSocket
import MADA_defs as MADADef
import MADA_util as MADAUtil


def check_maqs_status( maqs_sock ):

    print("Checking MAQS's status...")
    if MADAUtil.submit_to_maqs( maqs_sock, MADADef.PACKET_CHECKDAQ ) == False:
        print( "Status check for " + maqs_sock[3] + " failed, aborting..." )
        return 
    reply_data = maqs_sock[0].receive( )
    reply_val = int.from_bytes( reply_data ) & 0xff
    
    return reply_val.to_bytes( 1, "little" )
    

def check_macaron_status( macaron_sock ):

    print("Check MACARON status...")
    if MADAUtil.submit_to_macaron( macaron_sock, MADADef.PACKET_CHECKCTRL ) == False:
        print( "Status check for " + macaron_sock[3] + " failed, aborting..." )
        return

    reply_data = macaron_sock[0].receive( )
    reply_val = int.from_bytes( reply_data ) & 0xff
    
    return reply_val.to_bytes( 1, "little" )


def check_mascot_status( mascot_sock ):
    MADAUtil.submit_to_mascot( mascot_sock, MADADef.PACKET_LVCHECK )
    data = mascot_sock[0].receive( )
    return data


def check_reset_lv( mascot_sock, enable_swveto ):
    data = check_mascot_status( mascot_sock )
    if data == MADADef.PACKET_LVSTATUS_NG:
        print( f" === LV currents exceed threshold. LV reset start === " )
        print( )
        if enable_swveto == True:
            print( f"Software veto: ON" )
            MADAUtil.submit_to_macaron( MADADef.PACKET_SWVETO_ON )
            
        MADAUtil.submit_to_mascot( MADADef.PACKET_LVRESET )
        lv_reset_sleep = config_load["general"]["sleepLVReset"]
        print( f"LV resetting... (sleep time: {lv_reset_sleep} sec.)" )
        time.sleep( lv_reset_sleep )
        while True:
            MADAUtil.submit_to_mascot( MADADef.PACKET_LVCHECK )
            data = mascot_sock[0].receive( )
            if data == MADADef.PACKET_LVSTATUS_OK:
                print( f"LV reset successfully done!" )
                break

        if enable_swveto == True:
            print( f"Software veto: OFF" )
            MADAUtil.submit_to_macaron( MADADef.PACKET_SWVETO_OFF )
            
    print( )
    return


def kill_maqs_process( maqs_sock ):
    MADAUtil.submit_to_maqs( maqs_sock, MADADef.PACKET_KILLALL )
    return


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

    # start MACARON scaler
    MADAUtil.submit_to_macaron( MADADef.PACKET_SCALER_START )
        
    print( )
    print( f"===========================" )
    print( f" DAQ starting... " )
    print( f" period : {per_name}" )
    print( f"===========================" )

    max_files = 255
    fileID = 0
    while fileID < max_files:
        print( f"{fileID} / {max_files}" )

        # send software veto
        MADAUtil.submit_to_macaron( MADADef.PACKET_SWVETO_ON )
        print( f"Activate software veto: command submitted to MACARON" )

        # DAQ status check (and kill all processes)
        for maqs_sock in maqs_sock_arr:
            if check_maqs_status( maqs_sock ) != MADADef.CTRL_MAQS_STATE_IDLE:
                kill_maqs_process( maqs_sock )

        # send DAQ start flag to mascot
        MADAUtil.submit_to_mascot( MADADef.PACKET_DAQSTART )
        print( f"LV auto-reset from SCSM is locked: command submitted to MASCOT" )
        time.sleep( 1 )
        
        # check LV status
        check_reset_lv( mascot_sock, False )
        
        # configuration
        print( f"Vth and DAC parameter setting..." )
        MADAUtil.submit_to_maqs( MADADef.PACKET_SETVTHDAC )
        while True:
            if MADAUtil.process_running( MADADef.PY_MAQS_SETVTHDAC ) == True:
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

        while True:
            for maqs_sock in maqs_sock_arr:
                fileID_command = fileID.to_bytes( 1, "little" )
                daq_start_command = MADADef.CTRL_SYS_MIRACLUE + MADADef.CTRL_ROLE_MASTER + MADADef.CTRL_CMD_DAQSTART + fileID_command
                MADAUtil.submit_to_maqs( daq_start_command )
                timeout_itv = 0
                while True:
                    if check_maqs_status( maqs_sock ) == MADADef.CTRL_MAQS_STATE_DAQRUN:
                        print( f"===> {maqs_sock[3]} DAQ RUNNING" )
                        break
                    timeout_itv += 1
                    if timeout_itv <= 100:
                        print( f"ERROR: failed to boot {maqs_sock[3]} DAQ. aborting..." )
                        sys.exit( 1 )
        
        # DAQ enable
        print( f" ===========================================================" )
        print( f" DAQ enable ON" )
        print( f" ===========================================================" )
        MADAUtil.submit_to_macaron( MADADef.PACKET_DAQENABLE )
        print( f"Counter reset: command submitted to MACARON" )
        MADAUtil.submit_to_macaron( MADADef.PACKET_CNTRESET )
        print( f"Deactivate software veto: command submitted to MACARON" )
        MADAUtil.submit_to_macaron( MADADef.PACKET_SWVETO_OFF )
        print( )
        print( f"...DAQ RUNNING..." )
        print( )
        print( )
            
        # Status check
        while True:
            daq_end = False
            for maqs_sock in maqs_sock_arr:
                if check_maqs_status( maqs_sock ) == MADADef.CTRL_MAQS_STATE_IDLE:
                    print( f"DAQ file: {fileID} finished. file changing..." )
                    daq_end = True
                    break
            if daq_end == True:
                break
            check_reset_lv( mascot_sock, True )
            time.sleep( config_load["general"]["sleepStatusCheck"] )

        # file changing (next loop)
        MADAUtil.submit_to_macaron( MADADef.PACKET_DAQDISABLE )
        print( f"...DAQ END, file changing..." )
        print( )
        fileID += 1
        
    return

def daq_abort( ):
    
    print( )
    print( "===========================" )
    print( " DAQ aborting... " )
    print( "===========================" )

    # state control
    MADAUtil.submit_to_macaron( MADADef.PACKET_DAQDISABLE )
    MADAUtil.submit_to_macaron( MADADef.PACKET_SWVETO_OFF )
    MADAUtil.submit_to_mascot( MADADef.PACKET_DAQSTOP )

    # DAQ stop
    MADAUtil.submit_to_maqs( MADADef.PACKET_DAQSTOP )
    MADAUtil.submit_to_macaron( MADADef.PACKET_SCALER_STOP )
    
    return

def main( ):
    print( "** MADA start from MAMA **" )
    print( "** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **" )
    print( "** 2025 Aug by S. Higashino **" )

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

    print( " === Distributing config file to all MAQS servers ===")
    MADAUtil.divide_config( config_load )
    print( " === Distributing config file Done ===")
    
    try:
        daq_run( config_load, maqs_sock_arr, macaron_sock, mascot_sock )
    except KeyboardInterrupt:
        daq_abort( config_load, maqs_sock_arr, macaron_sock, mascot_sock )

    return    
    
if __name__ == "__main__":
    main( )
