#!/usr/bin/env python3

import os
import sys
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
SETALLDAC_EXE  = MADAHOME + "/bin/SetAllDAC"
READMEM_EXE    = MADAHOME + "/bin/ReadCtrlMem"


class SetAllDacError(RuntimeError):
    """Raised when SetAllDAC gets no reply from one or more boards."""


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

    targets = []
    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active'] == 1:
            ip = config_load['gigaIwaki'][x]['IP']
            if calin and ip != calin[0]:
                continue
            targets.append((x, config_load['gigaIwaki'][x]))

    # Launch every board's SetAllDAC first so the commands go out together,
    # then collect results, rather than waiting on each board in turn.
    procs = {}
    for name, data in targets:
        ip, Vth, DACfile, bias = data['IP'], data['Vth'], data['DACfile'], data['bias']

        # Apply Vth, DAC values and bias in one shot
        cmd = f"{SETALLDAC_EXE} {ip} {Vth} {DACfile} {bias}"
        if calin:
            cmd += " " + calin[1]
        print('Execute: ' + cmd)
        procs[name] = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    failed = []
    for name, proc in procs.items():
        stdout, _ = proc.communicate()
        print(stdout)
        if proc.returncode != 0:
            failed.append(name)

    # Memory-check logs are diagnostic, so still collect them for every
    # board (including ones that failed above) before raising.
    log_entries = []
    for name, data in targets:
        dt = datetime.datetime.now()
        log_file_name = LOGPATH + '/' + str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2) + "-" + str(dt.hour).zfill(2) + str(dt.minute).zfill(2) + str(dt.second).zfill(2) + "-" + name
        log_out = open(log_file_name, 'w')
        cmd = READMEM_EXE + " " + data['IP']
        log_entries.append((log_file_name, log_out, subprocess.Popen(cmd, shell=True, stdout=log_out)))

    for log_file_name, log_out, proc in log_entries:
        proc.wait()
        log_out.close()
        print("Memory check log: " + log_file_name)

    if failed:
        raise SetAllDacError(f'SetAllDAC got no reply from: {", ".join(failed)}')


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
    try:
        run_set_all_dac(config)
    except SetAllDacError as e:
        print(f'ERROR: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()