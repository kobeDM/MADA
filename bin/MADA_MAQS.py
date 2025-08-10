#!/usr/bin/python3

import argparse
from udp_util import UDPGenericSocket
import MADA_defs as MADADef

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

    if udpsock.receive( ) == MADADef.MADA_PACKET_DAQSTART:
        print( "DAQ: start" )
    else:
        print( "DAQ start failed..." )
        
    
    return


if __name__ == "__main__":
    main( )
