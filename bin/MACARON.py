#!/usr/bin/python3
import argparse
import subprocess
from subprocess import PIPE
from udp_util import UDPGenericSocket
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


def check_macaron_status( ):
    return


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
            daq_enable( True )
        elif data == MADADef.PACKET_DAQDISABLE:
            print( "Control: DAQ disable" )
            daq_enable( False )
        elif data == MADADef.PACKET_CNTRESET:
            print( "Control: Counter reset" )
            counter_reset( )
        elif data == MADADef.PACKET_CHECKCTRL:
            print( "Control: Check controller status" )
            check_macaron_status( )
        else:
            print( "Unknown message..." )


    return


if __name__ == "__main__":
    main( )
