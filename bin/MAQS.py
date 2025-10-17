#!/usr/bin/python3
import argparse
import subprocess
from subprocess import PIPE
from udp_util import UDPGenericSocket
import MADA_defs as MADADef
import MADA_util as MADAUtil


def start_maqs_daq( fileID ):
    cmd = f"{MADADef.PY_MAQS_RUNDAQ} -i {fileID}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    return


def abort_maqs_daq( ):
    MADAUtil.kill_process( f"{MADADef.PY_MAQS_RUNDAQ}" ) # runDAQ should be killed before MADA_iwaki process
    current_per = MADAUtil.get_current_period( )
    MADAUtil.kill_DAQ( MADADef.DEF_CONFIGFILE, current_per )
    return


def check_maqs_status( ):
    process_exist = False
    status = CTRL_MAQS_STATE_UNKNOWN
    if MADAUtil.process_running( PY_MAQS_RUNDAQ ) == True:
        status = CTRL_MAQS_STATE_DAQRUN
        process_exist = True
    if MADAUtil.process_running( PY_MAQS_SETVTHDAC ) == True:
        status = CTRL_MAQS_STATE_SETVTHDAC if process_running == False else CTRL_MAQS_STATE_OVERTASK
    if MADAUtil.process_running( PY_MAQS_VTHSCAN ) == True:
        status = CTRL_MAQS_STATE_VTHSCAN if process_running == False else CTRL_MAQS_STATE_OVERTASK
    if MADAUtil.process_running( PY_MAQS_DACSCAN ) == True:
        status = CTRL_MAQS_STATE_DACSCAN if process_running == False else CTRL_MAQS_STATE_OVERTASK

    if process_exist == False:
        status = CTRL_MAQS_STATE_IDLE
    return status


def kill_all_process( ):
    MADAUtil.kill_process( PY_MAQS_RUNDAQ )
    MADAUtil.kill_process( PY_MAQS_SETVTHDAC )
    MADAUtil.kill_process( PY_MAQS_VTHSCAN )
    MADAUtil.kill_process( PY_MAQS_DACSCAN )
    return


def config_set_vth_dac( ):
    cmd = f"{MADADef.PY_MAQS_SETVTHDAC}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    return


def config_vth_scan( ):
    cmd = f"{MADADef.PY_MAQS_VTHSCAN}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    return


def config_dac_scan( ):
    cmd = f"{MADADef.PY_MAQS_DACSCAN}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    return


def main( ):
    print( "** MADA MAQS Server starting... **" )
    print( "** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **" )
    print( "** 2025 Aug by S. Higashino **" )

    parser = argparse.ArgumentParser( )
    parser.add_argument( "-a", help="server IP address", default="localhost" )
    parser.add_argument( "-p", help="UDP port", default="9000" )

    args = parser.parse_args( )
    ip_address = (str)(args.a)
    udp_port = (int)(args.p)

    udpsock = UDPGenericSocket( True, 1024 )
    udpsock.initialize( ip_address, udp_port )

    while True:
        data = udpsock.receive( )
        
        if int.from_bytes( data, "little" ) & 0xffffff00).to_bytes( 4, "little" )  == MADADef.PACKET_DAQSTART:
            print( "DAQ: start" )
            fileID = ( int.from_bytes( data, "little" ) & 0xff )
            start_maqs_daq( fileID )
        elif data == MADADef.PACKET_DAQSTOP:
            print( "DAQ: stop" )
            abort_maqs_daq( )
        elif data == MADADef.PACKET_CHECKDAQ:
            print( "DAQ: status check" )
            check_maqs_status( )
        elif data == MADADef.PACKET_KILLALL:
            print( "DAQ: kill all processes" )
            kill_all_process( )
        elif data == MADADef.PACKET_SETVTHDAC:
            print( "Config: set Vth and DAC" )
            config_set_vth_dac( )
        elif data == MADADef.PACKET_VTHSCAN:
            print( "Config: run Vth scan" )
            config_vth_scan( )
        elif data == MADADef.PACKET_DACSCAN:
            print( "Config: run DAC scan" )
            config_dac_scan( )
        else:
            print( "Unknown message..." )

    return


if __name__ == "__main__":
    main( )
