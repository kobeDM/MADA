#!/usr/bin/env python3

import os
import json
import subprocess
import argparse

MADAHOME = os.environ['MADAHOME']
MADABIN = MADAHOME + '/bin'

SETAP = os.path.join(MADABIN, 'SetAP')

CONFIG = './MADA_config.json'

def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('io', type=int, choices=[0, 1], help='0/1')
    parser.add_argument('-c', '--config', default=CONFIG)
    args = parser.parse_args()
    return args

def run_set_ap(config_path, io, target_ip=None):
    with open(config_path, 'r') as file:
        config_load = json.load(file)

    for name, data in config_load.get('gigaIwaki', {}).items():
        if data.get('active') != 1:
            continue

        ip = data.get('IP')
        if target_ip and ip != target_ip:
            continue

        print('GigaIwaki: ' + name)
        print('  IP      : ' + ip)
        print('  IO      : ' + str(io))

        cmd = [SETAP, ip, str(io)]
        print('Execute : ' + ' '.join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        print('---')

def main():
    print("*** mada_set_ap.py start ***")

    args = arg_parser()
    io = args.io
    config = args.config

    run_set_ap(config, io)

    print("*** mada_set_ap.py end ***")

if __name__ == "__main__":
    main()