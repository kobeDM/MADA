#!/usr/bin/python3
import os
import subprocess
import argparse
import glob
import json
from subprocess import PIPE
import MADA_defs as MADADef
import MADA_util as MADAUtil

    
def main( ):

    print( "**Vth scan start on MAQS servers**" )
    print( "**Miraclue Argon DAQ (http://github.com/kobeDM/MADA)**" )
    print( "**2025 Aug by S. Higashino**" )

    # load config file
    mada_config_path = MADADef.DEF_CONFIGFILE
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
        VthScanWidth = config_load["GBKB"][gbkb_name]["VthScanWidth"]
        VthScanStep  = config_load["GBKB"][gbkb_name]["VthScanStep"]
        VthMin       = VthVal - VthScanWidth
        VthMax      = VthVal + VthScanWidth
        print( f"IP:       {activeIP}"     )
        print( f"Vth min.: {VthMin}"       )
        print( f"Vth max.: {VthMax}"      )
        print( f"Vth step: {VthScanWidth}" )

        newrun = MADAUtil.make_new_scan_run( MADADef.DEF_VTHSCAN_HEADER )
        os.mkdir( newrun )
        os.chdir( newrun )
        print( f"Making and changing directory to {newrun}" )

        # Vth scan
        cmd = f"{MADADef.CPP_MADA_VTHSCAN} {activeIP} {VthMin} {VthMax} {VthScanStep}"
        print( f"Execute: {cmd}" )
        subprocess.run( cmd, shell = True )
        os.chdir("../")

        # Vth analysis
        cmd = f"{MADADef.CPP_MADA_VTHANA} {newrun} {activeIP} {VthMin} {VthMax} {VthScanStep}"
        print( f"Execute: {cmd}" )
        subprocess.run( cmd, shell = True )

    os.chdir("../")
    return

if __name__ == "__main__":
    main( )


