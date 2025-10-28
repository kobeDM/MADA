#!/usr/bin/python3
import os
import argparse
import subprocess
from subprocess import PIPE
from udp_util import UDPGenericSocket
import json
import MADA_defs as MADADef
import MADA_util as MADAUtil


def main( ):
    print( "** MADA MACARON scaler starting... **" )
    print( "** Miraclue Argon DAQ (http://github.com/kobeDM/MADA) **" )
    print( "** 2025 Sep. by S. Higashino **" )

    parser = argparse.ArgumentParser( )
    parser.add_argument( "-c", help = "config file name", default = MADADef.DEF_CONFIGFILE )
    args = parser.parse_args( )

    mada_config_path = args.c
    if os.path.isfile( mada_config_path ) == False:
        mada_config_path = f"{MADADef.DEF_MACARON_CONFIG}"
    with open( mada_config_path, "r" ) as config_open :
        config_load = json.load( config_open )

    scaler_path = config_load["MACARON"]["scalerdir"]
    run_path = config_load["general"]["rundir"]
    det_name = config_load["general"]["detector"]
    current_dir = os.path.basename( scaler_path )
    run_current_path = f"{run_path}/{det_name}/{current_dir}"
    
    per_number = 0
    while os.path.isdir( f"{run_current_path}/per{str(per_number).zfill(4)}" ) == True:
        per_number += 1
    current_per = per_number - 1

    cmd = f"{MADADef.CPP_MACARON_SCALER} {scaler_path} {current_per}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    stdout  = proc.communicate()
    
    return


if __name__ == "__main__":
    main( )
