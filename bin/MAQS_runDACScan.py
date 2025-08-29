#!/usr/bin/python3
import os
import subprocess
import argparse
import glob
from subprocess import PIPE
import MADA_defs as MADADef
import MADA_util as MADAUtil

    
def main( ):

    print( "**DAC scan start on MAQS servers**" )
    print( "**Miraclue Argon DAQ (http://github.com/kobeDM/MADA)**" )
    print( "**2025 Aug by S. Higashino**" )

    # load config file
    MADAUtil.get_config( )
    with open( mada_config_path, "r" ) as config_open :
        config_load = json.load( config_open )
        
    # prepare and change scan working directory
    scan_work_dir = MADADef.DEF_SCAN_DIR
    if os.path.isdir( scan_work_dir ) == False:
        os.mkdir( scan_work_dir )
    os.chdir( scan_work_dir )
    
    gbkb_info_arr = []
    for gbkb_name in config_load[ "GBKB" ]:
        if config_load["GBKB"][gbkb_name]["active"] == 0: continue
    
        activeIP     = config_load["GBKB"][gbkb_name]["IP"]
        VthVal       = config_load["GBKB"][gbkb_name]["Vth"]
        print( f"IP:  {activeIP}" )
        print( f"Vth: {VthVal}" )

        newrun = MADAUtil.make_new_scan_run( MADADef.DEF_DACSCAN_HEADER )
        os.mkdir( newrun )
        os.chdir( newrun )
        print( f"Making and changing directory to {newrun}" )

        # DAC scan
        cmd = f"{MADADef.CPP_MADA_DACSCAN} {activeIP} {VthVal}"
        print( f"Execute: {cmd}" )
        subprocess.run( cmd, shell = True )
        os.chdir("../")

        # DAC analysis
        cmd = f"{MADADef.CPP_MADA_DACANA} {newrun} {(activeIP.split('.'))[3]}"
        print( f"Execute: {cmd}" )
        subprocess.run( cmd, shell = True )

    os.chdir("../")
    return

if __name__ == "__main__":
    main( )


