#!/usr/bin/env python3

import os
import argparse
import json
import datetime

import subprocess
from subprocess import PIPE

MADAHOME    = os.environ['MADAHOME']
IWAKIANAHOME = os.environ['IWAKIANAHOME']
MADABIN     = MADAHOME + '/bin'
IWAKIANABIN = IWAKIANAHOME + '/bin'

#scripts
FETCHCON    = "MADA_fetch_config.py"

#configs
CONFIG      = "MADA_config.json"

# binary
LOGPATH     = MADAHOME + "/config/DAClog"
SETVTH_EXE  = IWAKIANABIN  + "/SetVth"
SETDAC_EXE  = IWAKIANABIN  + "/SetDAC"
READMEM_EXE = IWAKIANABIN  + "/read_CtrlMem"

def parser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("config_file", type=str, nargs='?', const=None, help='config file', default=CONFIG)
    args = argparser.parse_args()

    return args

def main():
    print('### MADA_SetAllDAC.py start ###')

    args = parser()
    if args.config_file:
        config = args.config_file

    # Fetch config file
    cmd = MADABIN + '/' + FETCHCON
    print('Execute: ' + cmd)
    ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
    print(ret.stdout)
            
    #load config file
    activeIP = []
    with open(config, 'r') as config_open:
        config_load = json.load(config_open)

    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active'] == 1:
            activeIP.append(config_load['gigaIwaki'][x]['IP'])
            name    = x
            IP      = config_load['gigaIwaki'][x]['IP']
            Vth     = config_load['gigaIwaki'][x]['Vth']
            DACfile = config_load['gigaIwaki'][x]['DACfile']

            # Apply DAC
            cmd = SETDAC_EXE + " " + IP + " " + DACfile
            print('Execute: ' + cmd)
            subprocess.run(cmd, shell=True)

            # Apply Vth
            cmd = SETVTH_EXE + " " + IP + " " + str(Vth)
            print('Execute: ' + cmd)
            subprocess.run(cmd, shell=True)

            dt   = datetime.datetime.now()
            flog_name = LOGPATH + '/' + str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2) + "-" + str(dt.hour).zfill(2) + str(dt.minute).zfill(2) + str(dt.second).zfill(2) + "-" + name
            with open(flog_name, 'w') as log_out:
                cmd = READMEM_EXE + " " + IP
                subprocess.run(cmd, shell=True, stdout=log_out)
                print("Memory check log: " + flog_name)

    print('### MADA_SetAllDAC.py end ###')

if __name__ == '__main__':
    main()