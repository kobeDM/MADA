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

parser = argparse.ArgumentParser()
parser.add_argument("-c",help="config file name",default=CONFIG)
args = parser.parse_args()
CONFIG = args.c

def print_and_exe(cmd):
    print("execute:", cmd)
    subprocess.run(cmd,shell=True)

if os.path.isdir(LOGPATH) == False:
   cmd = "mkdir " + LOGPATH
   subprocess.run(cmd,shell=True)
   
if os.path.isfile(CONFIG):
   print(CONFIG, "exists.")
else:
   cmd = MADABIN + '/' + FETCHCON
   subprocess.run(cmd, shell=True)
      

with open(CONFIG) as config_open:
    config_load = json.load(config_open)

for i in config_load['gigaIwaki']:
    IP      = config_load['gigaIwaki'][i]['IP']
    Vth     = config_load['gigaIwaki'][i]['Vth']
    DACfile = config_load['gigaIwaki'][i]['DACfile']
        
    #DAC and Vth writing
    cmd = SETDAC_EXE + " " + IP + " " + DACfile
    print_and_exe(cmd)
    cmd=SETVth_EXE+" "+IP+" "+str(Vth)
    print_and_exe(cmd)

    dt   = datetime.datetime.now()
    flog = LOGPATH + '/' + str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2) + "-"+ str(dt.hour).zfill(2) + str(dt.minute).zfill(2) + str(dt.second).zfill(2)
    with open(flog,'w') as log_out:
        cmd = READMEM_EXE + " " + IP
        subprocess.run(cmd,shell=True,stdout=log_out)
    print("memory check log:", flog)
