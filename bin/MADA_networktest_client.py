#!/usr/bin/python3

import time
import socket
import argparse
from udp_util import UDPGenericSocket

socket_array = []
socket_array.append( ( UDPGenericSocket( False, 1024 ), '10.37.0.181', 9001  ) )
socket_array.append( ( UDPGenericSocket( False, 1024 ), '10.37.0.182', 9002  ) )


def main( ):

    for socket in socket_array:
        socket[0].initialize( socket[1], socket[2] )
        
    return

if __name__ == "__main__":
    main( )
