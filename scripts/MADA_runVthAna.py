#!/usr/bin/env python3
import os
import subprocess
import argparse
from subprocess import PIPE
import json
from csv import reader

print('### MADA_runVthAna.py start ###')

MADAHOME  = os.environ['MADAHOME']

EXE       = MADAHOME + '/bin/Vth_Analysis'
SKEL      = MADAHOME + '/rootmacro/ShowVth_skel.cxx'
SHOW_CODE = MADAHOME + '/rootmacro/ShowVth.cxx'

#configs
CONFIG = "MADA_config.json"

def parser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("runID", type=str, nargs='?', const=None, help='[runID]')
    argparser.add_argument("-b", "--batch", help="batch mode", dest='batch', action="store_true")
    args = argparser.parse_args()
    
    return args

def run_command(cmd):
    print("execute: " + cmd)
    subprocess.run(cmd, shell=True)

def main():
    args = parser()
    if args.runID:
        run = args.runID
        print("runID:", run)
    else:
        print("Error: RUN ID is not selected.")
        exit(1)

    if args.batch:
        print("batch mode")

    configfile = run + '/scan_config.out'
    print("Config file:", configfile)

    with open(configfile, 'r') as csv_file:
        csv_reader = reader(csv_file, delimiter = ' ')
        config = list(csv_reader)

    l_Vth = [line for line in config if 'Vth(lower):' in line]
    VthLow = l_Vth[0][1]
    print('Vth(lower):', VthLow)

    l_Vth = [line for line in config if 'Vth(upper):' in line]
    VthHigh = l_Vth[0][1]
    print('Vth(upper):', VthHigh)

    l_Vth = [line for line in config if 'Vth(delta):' in line]
    VthStep = l_Vth[0][1]
    print('Vth(delta):', VthStep)

    l_IP = [line for line in config if 'IP:' in line]
    IP = l_IP[0][1]
    print('IP:', IP)

    if os.path.exists(CONFIG):
        config_open= open(CONFIG,'r')
        config_load = json.load(config_open)
        for x in config_load['gigaIwaki']:
            if IP == config_load['gigaIwaki'][x]['IP']:
                Vth=config_load['gigaIwaki'][x]['Vth']
    else:
        Vth = 0
        print('Config file is not exits in current directory.')
        print('Used default Vth:', Vth)


    EXECOM = EXE + " " + run + "/ " + VthLow + " " + VthHigh + " " + VthStep
    print("execute:",EXECOM)
    subprocess.run(EXECOM,shell=True)

    # fetch skelton file
    with open(SKEL, mode='r') as f:
        str_list = f.readlines()
        showcode = [ s.replace("RUNID",run).replace("IP", IP).replace("VTH", str(Vth))  for s in str_list ]
    with open(SHOW_CODE, mode='w') as f:
        f.writelines(showcode)

    if args.batch:
        cmd = 'root -b -q -l ' + SHOW_CODE
    else:
        cmd = 'root ' + SHOW_CODE

    run_command(cmd)

    print('### MADA_runVthAna.py end ###')

if __name__ == '__main__':
    main()