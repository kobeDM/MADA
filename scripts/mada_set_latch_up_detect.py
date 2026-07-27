#!/usr/bin/env python3

import os
import json
import subprocess
import argparse

MADAHOME = os.environ['MADAHOME']
MADABIN = MADAHOME + '/bin'

FETCHCONFIG = os.path.join(MADABIN, 'mada_fetch_config.py')
SETLATCHUPDETECT = os.path.join(MADABIN, 'SetLatchUpDetect')

CONFIG = './MADA_config.json'

def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('io', help='0/1')
    parser.add_argument('-c', '--config', default=CONFIG)
    args = parser.parse_args()
    return args


def run_set_latch_up_detect(config_path: str, io : int):
    with open(config_path, 'r') as file:
        config_load = json.load(file)

    for name, data in config_load.get('gigaIwaki', {}).items():
        if data.get('active') != 1:
            continue

        ip = data.get('IP')

        print('GigaIwaki: ' + name)
        print('  IP      : ' + ip)
        print('  IO      : ' + str(io))

        cmd = [SETLATCHUPDETECT, ip, str(io)]
        print('Execute : ' + ' '.join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        print('---')

def main():
    print("*** mada_set_latch_up_detect.py start ***")

    args = arg_parser()
    io = int(args.io)
    config = args.config

    if not os.path.isfile(config):
        print('Config file was not found. Fetching skelton file...')
        subprocess.run([FETCHCONFIG])
        config = CONFIG

    print('Config file: ' + config)
    print('---')

    with open(config, 'r') as file:
        config_load = json.load(file)

    run_set_latch_up_detect(config, io)

    print("*** mada_set_latch_up_detect.py end ***")

if __name__ == "__main__":
    main()