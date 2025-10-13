#!/usr/bin/python3
import os
import sys
import time
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


    datadir_name = config_load["general"]["datadir"]
    detector_name = config_load["general"]["detector"]
    current_dir_name = os.path.basename( os.getcwd( ) )
    for i in range( 6 ):
        maqs_name = f"MAQS{i+1}"
        config_filepath = f"{datadir_name}/{maqs_name}/{detector_name}/{current_dir_name}/{MADADef.DEF_CONFIGFILE}"
        dict = { }
        for index in config_load:
            if index == "general":
                dict.update( config_load["general"] )
            elif index == maqs_name:
                dict.update( config_load[maqs_name]["GBKB"] )
        with open( config_filepath, mode = "wt", encoding = "utf-8" ) as file:
            json.dump( dict, file, ensure_ascii = False, indent = 2 )

    
    try:
        daq_run( config_load, maqs_sock_arr, macaron_sock, mascot_sock )
    except KeyboardInterrupt:
        daq_abort( config_load, maqs_sock_arr, macaron_sock, mascot_sock )

    return    
    
if __name__ == "__main__":
    main( )
