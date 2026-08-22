#!/usr/bin/env python3

import os
import argparse
import json
import datetime

import subprocess
from subprocess import PIPE

MADAHOME    = os.environ['MADAHOME']

#scripts
FETCHCON    = MADAHOME + "/scripts/mada_fetch_config.py"

#configs
# DEFAULT_CONFIG      = MADAHOME + "/config/MADA_config_SKEL.json"
DEFAULT_CONFIG      = "MADA_config.json"

# binary
LOGPATH        = MADAHOME + "/config/DAClog"
SETVTH_EXE     = MADAHOME + "/bin/SetVth"
SETDAC_EXE     = MADAHOME + "/bin/SetDAC"
SETALLDAC_EXE  = MADAHOME + "/bin/SetAllDAC"
READMEM_EXE    = MADAHOME + "/bin/ReadCtrlMem"

def arg_parser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("config_file", type=str, nargs='?', const=None, help='config file', default=DEFAULT_CONFIG)
    argparser.add_argument("--calin", type=str, nargs=2, help='[IP] [ch (0-127)]', default=None)
    args = argparser.parse_args()
    return args

def make_logdir():
    if not os.path.exists(LOGPATH):
        os.makedirs(LOGPATH)

def run_set_all_dac(config_path, calin=None):
    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' does not exist.")
        return

    with open(config_path, 'r') as config_open:
        config_load = json.load(config_open)

    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active'] == 1:
            name    = x
            ip      = config_load['gigaIwaki'][x]['IP']
            Vth     = config_load['gigaIwaki'][x]['Vth']
            DACfile = config_load['gigaIwaki'][x]['DACfile']

            if calin and ip != calin[0]:
                continue

            # Apply DAC
            if calin:
                cmd = SETDAC_EXE + " " + ip + " " + DACfile + " " + calin[1]
            else:
                cmd = SETDAC_EXE + " " + ip + " " + DACfile
            print('Execute: ' + cmd)
            subprocess.run(cmd, shell=True)

            # Apply Vth
            cmd = SETVTH_EXE + " " + ip + " " + str(Vth)
            print('Execute: ' + cmd)
            subprocess.run(cmd, shell=True)

            dt   = datetime.datetime.now()
            log_file_name = LOGPATH + '/' + str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2) + "-" + str(dt.hour).zfill(2) + str(dt.minute).zfill(2) + str(dt.second).zfill(2) + "-" + name
            with open(log_file_name, 'w') as log_out:
                cmd = READMEM_EXE + " " + ip
                subprocess.run(cmd, shell=True, stdout=log_out)
                print("Memory check log: " + log_file_name)


# def run_set_all_dac(config_path):
#     if not os.path.exists(config_path):
#         print(f"Error: Config file '{config_path}' does not exist.")
#         return

#     with open(config_path, 'r') as config_open:
#         config_load = json.load(config_open)

#     for x in config_load['gigaIwaki']:
#         if config_load['gigaIwaki'][x]['active'] == 1:
#             name    = x
#             ip      = config_load['gigaIwaki'][x]['IP']
#             Vth     = config_load['gigaIwaki'][x]['Vth']
#             DACfile = config_load['gigaIwaki'][x]['DACfile']
#             bias    = config_load['gigaIwaki'][x]['bias']

#             print(f"Processing {name} (IP: {ip})")
#             print(f"  Vth: {Vth}, DACfile: {DACfile}, bias: {bias}")

#             # Apply DAC
#             cmd = f"{SETALLDAC_EXE} {ip} {Vth} {DACfile} {bias}"
#             print('Execute: ' + cmd)
#             subprocess.run(cmd, shell=True)


def main():
    make_logdir()
    args = arg_parser()
    if args.config_file:
        config = args.config_file
    calin = args.calin

    # get config file
    cmd = FETCHCON
    print('Execute: ' + cmd)
    ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
    print(ret.stdout)
            
    # run_set_all_dac(config, calin)
    run_set_all_dac(config)

if __name__ == '__main__':
    main()