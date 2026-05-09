#!/usr/bin/env python3

import os
import subprocess
import argparse
import json
import datetime

MADAHOME   = os.environ['MADAHOME']
MADABIN    = MADAHOME + '/bin'
CONFIGPATH = MADAHOME + '/config'

LOGPATH = MADAHOME + "/config/DAClog"
CONFIG  = "MADA_config.json"

FETCHCON = "fetch_config.py"

SETVth_EXE  = MADABIN + "/SetVth"
SETDAC_EXE  = MADABIN + "/SetDAC"
READMEM_EXE = MADABIN + "/read_CtrlMem"

reset = 0

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", help="config file name", default=CONFIG)
    args = parser.parse_args()

    return args

def print_and_exe(cmd):
    print("Execute: " + cmd)
    subprocess.run(cmd, shell=True)

def main():
    print('### MADA_SetDAC.py start ###')

    args = parser()
    config = args.c

    if os.path.isdir(LOGPATH) == False:
        cmd = "mkdir " + LOGPATH
        subprocess.run(cmd,shell=True)
    
    if os.path.isfile(config):
        print(config + " exists.")
    else:
        cmd = MADABIN + '/' + FETCHCON
        subprocess.run(cmd, shell=True)
        
    with open(config, 'r') as config_open:
        config_load = json.load(config_open)

    for x in config_load['gigaIwaki']:
        IP      = config_load['gigaIwaki'][x]['IP']
        Vth     = config_load['gigaIwaki'][x]['Vth']
        DACfile = config_load['gigaIwaki'][x]['DACfile']
            
        # DAC and Vth writing
        cmd = SETDAC_EXE + " " + IP + " " + DACfile
        print_and_exe(cmd)

        cmd = SETVth_EXE + " " + IP + " " + str(Vth)
        print_and_exe(cmd)

        # Writing log file
        dt   = datetime.datetime.now()
        flog = LOGPATH + '/' + str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2) + "-"+ str(dt.hour).zfill(2) + str(dt.minute).zfill(2) + str(dt.second).zfill(2)
        with open(flog,'w') as log_out:
            cmd = READMEM_EXE + " " + IP
            subprocess.run(cmd,shell=True,stdout=log_out)
        print("memory check log: " + flog)

    print('### MADA_SetDAC.py end ###')

if __name__ == '__main__':
    main()