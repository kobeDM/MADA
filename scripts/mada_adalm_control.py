#!/usr/bin/env python3

import os
import subprocess
import json
import argparse

MADAHOME = os.environ['MADAHOME']
ADALM_CTRL = MADAHOME + '/bin/AdalmControl'

def arg_parser():
    parser = argparse.ArgumentParser(description='Reset the counter of ADALM2000.')
    parser.add_argument('-c', '--config', default='MADA_config.json', help='Path to the configuration file (default: MADA_config.json).')
    parser.add_argument('-l', '--latch', type=int, default=1, help='Latch value (default: 1).')
    parser.add_argument('-i', '--idx', type=int, default=0, help='ADALM index (0: DAQ enable, 1: counter reset).')
    parser.add_argument('-w', '--width', type=float, default=None, help='Output a single latch-up/down pulse of this width in seconds, instead of a static latch.')
    args = parser.parse_args()
    return args

def load_config(config_path):
    with open(config_path, 'r') as f:
        config_load = json.load(f)
    return config_load

def get_adalm_serial(config_load, adalm_index=0):
    return config_load['ADALM']['MADALM_' + str(adalm_index)]['S/N']

def run_adalm_control(serial, latch, bg=False, width=None):
    cmd = ADALM_CTRL + " -s " + serial + " -l " + str(latch)
    if width is not None:
        cmd += " -w " + str(width)
    print('Execute: ' + cmd)
    if bg:
        subprocess.Popen(cmd, shell=True)
    else:
        subprocess.run(cmd, shell=True)

def main():
    args = arg_parser()

    config_path = args.config
    latch = args.latch
    adalm_index = args.idx
    width = args.width

    if not os.path.isfile(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        return

    config_load = load_config(config_path)
    serial = get_adalm_serial(config_load, adalm_index)

    run_adalm_control(serial, latch, width=width)


if __name__ == '__main__':
    main()