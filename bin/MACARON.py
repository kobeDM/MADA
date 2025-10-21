#!/usr/bin/python3
import argparse
import subprocess
from subprocess import PIPE
from udp_util import UDPGenericSocket
import json
import MADA_defs as MADADef
import MADA_util as MADAUtil


def daq_enable( is_enable ):
    enable_flag = 1 if is_enable == True else 0
    cmd = f"{MADADef.CPP_MACARON_DAQCTRL} {enable_flag}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    return


def counter_reset( ):
    cmd = f"{MADADef.CPP_MACARON_CNTRESET}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
    return


def testpulse_mode( is_tpmode ):
    cmd = f"{MADADef.CPP_MACARON_TPMODE} {is_tpmode}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
    return


def software_veto( is_swveto ):
    cmd = f"{MADADef.CPP_MACARON_SWVETO} {is_swveto}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
    return


def start_scaler( ):
    cmd = f"{MADADef.PY_MACARON_SCALER}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    return


def stop_scaler( ):
    MADAUtil.kill_process( f"{MADADef.PY_MACARON_SCALER}" )
    MADAUtil.kill_process( f"{MADADef.CPP_MACARON_SCALER}" )
    return


def check_macaron_status( ):
    status = MADADef.CTRL_MACARON_STATE_UNKNOWN

    cmd = f"{MADADef.CPP_MACARON_CHKSTATUS}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
    daq_enable_status = proc.returncode

    cmd = f"{MADADef.CPP_MACARON_CHKSTATUS} -tp"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
    tpmode_status = proc.returncode

    cmd = f"{MADADef.CPP_MACARON_CHKSTATUS} -sv"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
    swveto_status = proc.returncode
    
    if daq_enable_status == 0 and tpmode_status == 0 and swveto_status == 0:
        status = MADADef.CTRL_MACARON_STATE_IDLE
    elif daq_enable_status == 1 and tpmode_status == 0 and swveto_status == 0:
        status = MADADef.CTRL_MACARON_STATE_EN
    elif daq_enable_status == 0 and tpmode_status == 1 and swveto_status == 0:
        status = MADADef.CTRL_MACARON_STATE_TP
    elif daq_enable_status == 1 and tpmode_status == 1 and swveto_status == 0:
        status = MADADef.CTRL_MACARON_STATE_EN_TP
    elif daq_enable_status == 0 and tpmode_status == 0 and swveto_status == 1:
        status = MADADef.CTRL_MACARON_STATE_SV
    elif daq_enable_status == 1 and tpmode_status == 0 and swveto_status == 1:
        status = MADADef.CTRL_MACARON_STATE_SV_EN
    elif daq_enable_status == 0 and tpmode_status == 1 and swveto_status == 1:
        status = MADADef.CTRL_MACARON_STATE_SV_TP
    elif daq_enable_status == 1 and tpmode_status == 1 and swveto_status == 1:
        status = MADADef.CTRL_MACARON_STATE_SV_EN_TP
        
    return status


def main( ):
    print( "** MADA MACARON controller starting... **" )
    print( "** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **" )
    print( "** 2025 Sep. by S. Higashino **" )

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
        
        if data == MADADef.PACKET_DAQENABLE:
            print( "Control: DAQ enable" )
            daq_enable( 1 )
        elif data == MADADef.PACKET_DAQDISABLE:
            print( "Control: DAQ disable" )
            daq_enable( 0 )
        elif data == MADADef.PACKET_CNTRESET:
            print( "Control: Counter reset" )
            counter_reset( )
        elif data == MADADef.PACKET_TPMODE_ON:
            print( "Control: Test pluse mode: ON" )
            testpulse_mode( 1 )
        elif data == MADADef.PACKET_TPMODE_OFF:
            print( "Control: Test pluse mode: OFF" )
            testpulse_mode( 0 )
        elif data == MADADef.PACKET_SWVETO_ON:
            print( "Control: Software veto: ON" )
            software_veto( 1 )
        elif data == MADADef.PACKET_SWVETO_OFF:
            print( "Control: Software veto: OFF" )
            software_veto( 0 )
        elif data == MADADef.PACKET_SCALER_START:
            print( "Control: Start scaler" )
            start_scaler( )
        elif data == MADADef.PACKET_SCALER_STOP:
            print( "Control: Stop scaler" )
            stop_scaler( )
        elif data == MADADef.PACKET_CHECKCTRL:
            print( "Control: Check controller status" )
            macaron_status = check_macaron_status( )
            return_data = MADADef.CTRL_SYS_MIRACLUE + MADADef.CTRL_ROLE_SERVER + MADADef.CTRL_CMD_CHECKCTRL + macaron_status
            udpsock.send( return_data )
        else:
            print( "Unknown message..." )

    return


if __name__ == "__main__":
    main( )
