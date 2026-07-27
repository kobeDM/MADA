#!/usr/bin/env python3
import os
import subprocess
import argparse
import json
from csv import reader

MADAHOME  = os.environ['MADAHOME']

EXE_VTH_ANA = MADAHOME + '/bin/VthAnalysis'
EXE_SHOW    = MADAHOME + '/rootmacro/ShowVth.cxx'

#configs
CONFIG = "MADA_config.json"

def parser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("runID", type=str, nargs='?', const=None, help='[runID]')
    argparser.add_argument("-b", "--batch", help="batch mode", dest='batch', action="store_true")
    args = argparser.parse_args()
    
    return args

def run_command(cmd, cwd=None):
    print("execute: " + cmd)
    subprocess.run(cmd, shell=True, cwd=cwd)

def run_vth_ana(run, batch=False):
    print("runID:", run)
    if batch:
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

    cmd = EXE_VTH_ANA + " ./ " + VthLow + " " + VthHigh + " " + VthStep
    run_command(cmd, cwd=run)

    show_args = '"' + run + '", "' + IP + '", ' + str(Vth)
    if batch:
        cmd = "root -b -q -l '" + EXE_SHOW + "(" + show_args + ")'"
    else:
        cmd = "root '" + EXE_SHOW + "(" + show_args + ")'"

    run_command(cmd, cwd=run)

def main():
    print('### mada_run_vth_ana.py start ###')

    args = parser()
    if not args.runID:
        print("Error: RUN ID is not selected.")
        exit(1)

    run_vth_ana(args.runID, args.batch)

    print('### mada_run_vth_ana.py end ###')

if __name__ == '__main__':
    main()