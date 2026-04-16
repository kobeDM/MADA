#!/usr/bin/env python3

import os
import json
import subprocess
import argparse

MADAHOME = os.environ['MADAHOME']
MADABIN = MADAHOME + '/bin'

FETCHCONFIG = os.path.join(MADABIN, 'MADA_fetch_config.py')
SETADCBIAS = os.path.join(MADABIN, 'SetADCBias')

CONFIG = './MADA_config.json'

def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default=CONFIG)
    args = parser.parse_args()
    return args

def main():
    print("### MADA_SetADCBias.py start ###")

    args = arg_parser()
    config = args.config

    if not os.path.isfile(config):
        print('Config file was not found. Fetching skelton file...')
        subprocess.run([FETCHCONFIG])
        config = CONFIG

    print('Config file: ' + config)
    print('---')

    with open(config, 'r') as file:
        config_load = json.load(file)

    for name, data in config_load.get('gigaIwaki', {}).items():
        if data.get('active') != 1:
            continue

        ip = data.get('IP')
        bias = data.get('bias')

        print('GigaIwaki: ' + name)
        print('  IP      : ' + ip)
        print('  ADC bias: ' + str(bias))

        cmd = [SETADCBIAS, ip, str(bias)]
        print('Execute : ' + ' '.join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        print('---')

    print("### MADA_SetADCBias.py end ###")

if __name__ == "__main__":
    main()