#!/usr/bin/python3
import os
import argparse
import subprocess
from subprocess import PIPE
from udp_util import UDPGenericSocket
import json
import MADA_defs as MADADef
import MADA_util as MADAUtil
import MASCOT_LVCtrl as LVCtrl

def daq_start( ):
    if os.path.isfile( MADADef.LOCK_FILE_FULLPATH_AUTORESET ) == True:
        print( "WARNING: AUTO RESET lock file already exists. MADA DAQ might be running now." )
        return
    
    cmd = f"touch {MADADef.LOCK_FILE_FULLPATH_AUTORESET}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
    if proc.returncode ==  0:
        print( f"{MADADef.LOCK_FILE_FULLPATH_AUTORESET} successfully created." )
    else:
        print( f"ERROR: failed to create {MADADef.LOCK_FILE_FULLPATH_AUTORESET}." )
        
    return

def daq_stop( ):
    if os.path.isfile( MADADef.LOCK_FILE_FULLPATH_AUTORESET ) == False:
        print( "WARNING: AUTO RESET lock file not found. MADA DAQ might be already killed." )
        return
    
    cmd = f"rm {MADADef.LOCK_FILE_FULLPATH_AUTORESET}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
    if proc.returncode ==  0:
        print( f"{MADADef.LOCK_FILE_FULLPATH_AUTORESET} successfully removed." )
    else:
        print( f"ERROR: failed to remove {MADADef.LOCK_FILE_FULLPATH_AUTORESET}." )
    
    return

def lv_check( ):
    retVal = True
    if os.path.isfile( MADADef.DEF_LV_CONFIGFILE ) == False:
        cmd = f"cp {MADADef.MADA_ENV_PATH}/config/{MADADef.DEF_LV_CONFIGFILE}"
        proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
        proc.communicate( )
        if proc.returncode == 0:
            print( f"{MADADef.DEF_LV_CONFIGFILE} copied from MADA repository" )
        else:
            print( f"Failed to copy {MADADef.DEF_LV_CONFIGFILE} from MADA repository" )
            return retVal
        
    with open( MADADef.DEF_LV_CONFIGFILE, "r" ) as config_open :
        config = json.load( config_open )
    dev_file = MADADef.DEF_LV_USBDEVFILE
    curr_lim = config["devices"]["currentlimit"]
    curr_meas = []
    volt_meas = []
    dev_list = LVCtrl.sort_devices( dev_file, config )
    for ch in range( len( dev_list ) ):
        curr_val = LVCtrl.send_command( dev_list[ch], MADADef.LV_QUERY_GET_CURRENT )
        curr_meas.append( float( curr_val.strip( ) ) )
        volt_val = LVCtrl.send_command( dev_list[ch], MADADef.LV_QUERY_GET_VOLTAGE )
        volt_meas.append( float( volt_val.strip( ) ) )
    if curr_meas[1] > curr_lim[1] or curr_meas[2] > curr_lim[2]:
        retVal = False
    
    return retVal


def lv_reset( ):
    if os.path.isfile( MADADef.DEF_LV_CONFIGFILE ) == False:
        cmd = f"cp {MADADef.MADA_ENV_PATH}/config/{MADADef.DEF_LV_CONFIGFILE}"
        proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
        proc.communicate( )
        if proc.returncode == 0:
            print( f"{MADADef.DEF_LV_CONFIGFILE} copied from MADA repository" )
        else:
            print( f"Failed to copy {MADADef.DEF_LV_CONFIGFILE} from MADA repository" )
            return False
        
    with open( MADADef.DEF_LV_CONFIGFILE, "r" ) as config_open :
        config = json.load( config_open )
    dev_file = MADADef.DEF_LV_USBDEVFILE
    dev_list = LVCtrl.sort_devices( dev_file, config )
    itv_rbt = config["interval"]["reboot"]
    print( "+/- 2.5 V reset." )
    LVCtrl.send_command( dev_list[1], MADADef.LV_QUERY_OUTPUT_OFF )
    LVCtrl.send_command( dev_list[2], MADADef.LV_QUERY_OUTPUT_OFF )
    time.sleep( itv_rbt )
    LVCtrl.send_command( dev_list[1], MADADef.LV_QUERY_OUTPUT_ON )
    LVCtrl.send_command( dev_list[2], MADADef.LV_QUERY_OUTPUT_ON )

    return True


def main( ):
    print( "** MADA MASCOT SCSM starting... **" )
    print( "** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **" )
    print( "** 2025 Oct. by S. Higashino **" )

    parser = argparse.ArgumentParser( )
    parser.add_argument( "-a", help="server IP address", default='localhost' )
    parser.add_argument( "-p", help="UDP port", default='9000' )

    args = parser.parse_args( )
    ip_address = (str)(args.a)
    udp_port = (int)(args.p)

    udpsock = UDPGenericSocket( True, 1024 )
    udpsock.initialize( ip_address, udp_port )

    while True:
        data = udpsock.receive( )
        
        if data == MADADef.PACKET_DAQSTART:
            print( "SCSM: DAQ start" )
            daq_start( )
        elif data == MADADef.PACKET_DAQSTOP:
            print( "SCSM: DAQ stop" )
            daq_stop( )
        elif data == MADADef.PACKET_LVCHECK:
            print( "SCSM: LV check" )
            lv_OK = lv_check( )
            if lv_OK == True:
                udpsock.send( MADADef.PACKET_LVSTATUS_OK ) 
            else:
                udpsock.send( MADADef.PACKET_LVSTATUS_NG ) 
        elif data == MADADef.PACKET_LVRESET:
            print( "SCSM: LV reset" )
            if lv_reset( ) == True:
                print( "Succeeded in resetting LV" )
            else:
                print( "Failed to reset LV..." )
        else:
            print( "Unknown message..." )


    return


if __name__ == "__main__":
    main( )
