#!/usr/bin/python3
import os
import sys
import time
import argparse
import json
from udp_util import UDPGenericSocket
import MADA_defs as MADADef
import MADA_util as MADAUtil


def main( ):
    print( "** MADA divide config to MAQS's **" )
    print( "** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **" )
    print( "** 2025 Oct by S. Higashino **" )

    parser = argparse.ArgumentParser( )
    parser.add_argument( "-c", help = "config file name", default = MADADef.DEF_CONFIGFILE )
    args = parser.parse_args()

    mada_config_path = args.c
    MADAUtil.get_config( )
    with open( mada_config_path, "r" ) as config_open :
        config_load = json.load( config_open )

    MADAUtil.divide_config( config_load )

    return    
    
if __name__ == "__main__":
    main( )
