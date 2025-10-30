#!/usr/bin/python3
import subprocess, os,sys
import argparse
import json
import datetime
from subprocess import PIPE
import MADA_defs as MADADef

LOGPATH     = f"{MADADef.HOME_ENV_PATH}/miraclue/log/DAC"
SETVth_EXE  = f"{MADADef.MADA_ENV_PATH}/bin/SetVth"
SETDAC_EXE  = f"{MADADef.MADA_ENV_PATH}/bin/SetDAC"
READMEM_EXE = f"{MADADef.MADA_ENV_PATH}/bin/read_CtrlMem"

def main( ):

    argparser = argparse.ArgumentParser( )
    argparser.add_argument( "config_file", type = str, nargs = "?", const = None, help = "config file" )
    args = argparser.parse_args( )
    
    config_filename = MADADef.DEF_CONFIGFILE
    if args.config_file:
        config_filename = args.config_file
        print( "DAC config file:", config_filename )

    config_open = open( config_filename, "r" )
    config_load = json.load( config_open )
    activeIP = []
    for gbkb_name in config_load["GBKB"]:
        if config_load["GBKB"][gbkb_name]["active"] == 1:
            activeIP.append( config_load["GBKB"][gbkb_name]["IP"] )
            IP      = config_load["GBKB"][gbkb_name]["IP"]
            Vth     = config_load["GBKB"][gbkb_name]["Vth"]
            DACfile = config_load["GBKB"][gbkb_name]["DACfile"]
            print( config_load["GBKB"][gbkb_name]["IP"] )

            cmd = f"{SETDAC_EXE} {IP} {DACfile}"
            print( f"Execute: {cmd}" )
            subprocess.run( cmd, shell = True )

            cmd = f"{SETVth_EXE} {IP} {Vth}"
            print( f"Execute: {cmd}" )
            subprocess.run( cmd, shell = True )

            dt = datetime.datetime.now( )
            flog = f"{LOGPATH}{dt.year}{str(dt.month).zfill(2)}{str(dt.day).zfill(2)}-{str(dt.hour).zfill(2)}{str(dt.minute).zfill(2)}{str(dt.second).zfill(2)}-{gbkb_name}"
            with open( flog, "w" ) as log_out:
                cmd = f"{READMEM_EXE} {IP}"
                subprocess.run( cmd, shell = True, stdout = log_out )
                print( f"memory check log: {flog}" )    

    
if __name__ == "__main__":
    main( )


