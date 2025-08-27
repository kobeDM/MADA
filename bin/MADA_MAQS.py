#!/usr/bin/python3
import argparse
import subprocess
from subprocess import PIPE
from udp_util import UDPGenericSocket
import MADA_defs as MADADef
import MADA_util as MADAUtil

def start_maqs_daq( ):

    cmd = f"{MADADef.PY_MAQS_RUNDAQ}"
    proc = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=None)
    
    return

def abort_maqs_daq( ):

    MADAUtil.kill_process( f"{MADADef.PY_MAQS_RUNDAQ}" ) # runDAQ should be killed before MADA_iwaki process
    current_per = MADAUtil.get_current_period( )
    MADAUtil.kill_DAQ( MADADef.DEF_CONFIGFILE, current_per )
    
    return

def check_maqs_status( ):

    return

def config_set_vth_dac( ):
    
    cmd = f"{MADADef.PY_MAQS_SETVTHDAC}"
    proc = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=None)
    
    return

def main( ):
    
    print("** MADA MAQS Server starting... **")
    print("** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **")
    print("** 2025 Aug by S. Higashino **")

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
            print( "DAQ: start" )
            start_maqs_daq( )
        elif data == MADADef.PACKET_DAQSTOP:
            print( "DAQ: stop" )
            abort_maqs_daq( )
        elif data == MADADef.PACKET_CHECKDAQ:
            print( "DAQ: status check" )
        elif data == MADADef.PACKET_SETVTHDAC:
            print( "Config: set Vth and DAC" )
            config_set_vth_dac( )
        else:
            print( "Unknown message..." )

            
    return


if __name__ == "__main__":
    main( )
