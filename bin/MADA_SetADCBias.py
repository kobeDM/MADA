#!/usr/bin/env python3

import os
import sys
import json
import subprocess
import argparse

MADAHOME = os.environ['MADAHOME']
IWAKIANAHOME = os.environ['IWAKIANAHOME']
MADABIN = MADAHOME + '/bin'
IWAKIANABIN = IWAKIANAHOME + '/bin'

FETCHCONFIG = MADABIN + '/MADA_fetch_config.py'
SETADCBIAS = IWAKIANABIN + '/SetADCBias'

# default value
CONFIG = './MADA_config.json'

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='config file path', default=CONFIG)
    args = parser.parse_args()
    
    return args

def main():
    print("### MADA_SetADCBias.py start ###")

    args = parser()
    config = args.config
    if (os.path.isfile(config)):
        print('Config file: ' + config)
    else:
        print('Config file was not found. Fetching skelton file...')
        cmd = FETCHCONFIG
        print('Execute: ' + cmd)
        subprocess.run(cmd, shell=True)
        config = CONFIG
    print('---')

    with open(config, 'r') as file:
        config_load = json.load(file)
    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active'] == 1:
            ip = config_load['gigaIwaki'][x]['IP']
            bias = config_load['gigaIwaki'][x]['bias']

        print('GigaIwaki: ' + x)
        print('  IP      : ' + ip)
        print('  ADC bias: ' + str(bias))
        cmd = SETADCBIAS + ' ' + ip + ' ' + str(bias)
        print('Execute : ' + cmd)
        stdout = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
        print(stdout)
        print('---')

    print("### MADA_SetADCBias.py end ###")

if __name__ == "__main__":
    main()