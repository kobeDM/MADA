#!/usr/bin/env python3

import os
import argparse
import json
import datetime

import subprocess
from subprocess import PIPE

print('### MADA_SetAllDAC.py start ###')

MADAHOME = os.environ['MADAHOME']
MADABIN  = MADAHOME + '/bin'

#scripts
FETCHCON  = "/MADA_fetch_config.py"
# findADALM = "findADALM2000.py"
SETDAC    = "/MADA_SetAllDACs.py"

#configs
CONFIG      = "/MADA_config.json"
CONFIG_SKEL = "/MADA_config_SKEL.json"

# MADAPATH = "/home/msgc/miraclue/MADA/bin/"
# DACPATH  = "/home/msgc/miraclue/MADA/bin/"
LOGPATH     = MADAHOME + "/config/DAClog"
SETVth_EXE  = MADABIN + "/SetVth"
SETDAC_EXE  = MADABIN + "/SetDAC"
READMEM_EXE = MADABIN + "/read_CtrlMem"

# Check arguments
argparser = argparse.ArgumentParser()
argparser.add_argument("config_file", type=str, nargs='?', const=None, help='config file')
args = argparser.parse_args()

if args.config_file:
    CONFIG = args.config_file

# Fetch config file
cmd = MADABIN + FETCHCON
print('Execute:', cmd)
ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
print(ret.stdout)
        
#load config file
# config_open = open(CONFIG, 'r')
# config_load = json.load(config_open)
activeIP = []
with open(CONFIG, 'r') as config_open:
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
        print('Execute:', cmd)
        subprocess.run(cmd, shell=True)

        # Apply Vth
        cmd = SETVth_EXE + " " + IP + " " + str(Vth)
        print('Execute:', cmd)
        subprocess.run(cmd, shell=True)

        dt   = datetime.datetime.now()
        flog = LOGPATH + '/' + str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2) + "-" + str(dt.hour).zfill(2) + str(dt.minute).zfill(2) + str(dt.second).zfill(2) + "-" + name
        with open(flog, 'w') as log_out:
            cmd = READMEM_EXE + " " + IP
            subprocess.run(cmd, shell=True, stdout=log_out)
            print("Memory check log:", flog)

print('### MADA_SetAllDAC.py end ###')
