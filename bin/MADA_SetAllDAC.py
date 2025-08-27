#!/usr/bin/python3
import subprocess, os,sys
import argparse
import json
import datetime
from subprocess import PIPE
import MADA_defs as MADADef

#configs
CONFIG="MADA_config.json"
CONFIG_SKEL="MADA_config_SKEL.json"

LOGPATH     = f"{MADADef.HOME_ENV_PATH}/miraclue/log/DAC"
SETVth_EXE  = f"{MADADef.MADA_ENV_PATH}/bin/SetVth"
SETDAC_EXE  = f"{MADADef.MADA_ENV_PATH}/bin/SetDAC"
READMEM_EXE = f"{MADADef.MADA_ENV_PATH}/bin/read_CtrlMem"

def parser():
    argparser=argparse.ArgumentParser()
    argparser.add_argument("config_file",type=str,nargs='?',const=None,help='config file')
    opts=argparser.parse_args()
    return(opts)


def p_and_e(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd,shell=True)




def main( ):

    args=parser()
    config_filename = MADADef.DEF_CONFIGFILE
    if args.config_file:
        config_filename = args.config_file
        print( "DAC config file:", config_filename )

    config_open = open( config_filename, 'r' )
    config_load = json.load( config_open )
    activeIP = []
    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active']==1:
            activeIP.append(config_load['gigaIwaki'][x]['IP'])

            name=x
            IP=config_load['gigaIwaki'][x]['IP']
            Vth=config_load['gigaIwaki'][x]['Vth']
            DACfile=config_load['gigaIwaki'][x]['DACfile']

            print(config_load['gigaIwaki'][x]['IP'])

            cmd=SETDAC_EXE+" "+IP+" "+DACfile
            p_and_e(cmd)

            cmd=SETVth_EXE+" "+IP+" "+str(Vth)

            p_and_e(cmd)

            dt=datetime.datetime.now()
            flog=LOGPATH+str(dt.year)+str(dt.month).zfill(2)+str(dt.day).zfill(2)+"-"+str(dt.hour).zfill(2)+str(dt.minute).zfill(2)+str(dt.second).zfill(2)+"-"+name
            with open(flog,'w') as log_out:
                cmd=READMEM_EXE+" "+IP
                subprocess.run(cmd,shell=True,stdout=log_out)
                print("memory check log:"+flog)    

    
if __name__ == "__main__":
    main( )


