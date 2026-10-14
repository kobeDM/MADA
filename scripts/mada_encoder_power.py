#!/usr/bin/env python3

import argparse
import sys

from mada_config import load_config, latch_up_detect_enabled
from mada_errors import MadaError
from mada_set_ap import run_set_ap
from mada_set_all_dac import run_set_all_dac
from mada_set_latch_up_detect import run_set_latch_up_detect

CONFIG = './MADA_config.json'

def arg_parser():
    parser = argparse.ArgumentParser(description='Power up/down the GigaIwaki encoder (regulator, DAC/Vth, latch-up detection).')
    parser.add_argument('io', type=int, choices=[0, 1], help='0: power down, 1: power up')
    parser.add_argument('-c', '--config', default=CONFIG)
    args = parser.parse_args()
    return args

def run_encoder_power_up(config_path, calin=None, require_monitor=False):
    print('Activating Regulator...')
    run_set_ap(config_path, io=1, require_monitor=require_monitor)

    print('Setting DAC values, Vth and ADC bias...')
    run_set_all_dac(config_path, calin=calin)

    if latch_up_detect_enabled(load_config(config_path)):
        print('Activating Latch Up Detection...')
        run_set_latch_up_detect(config_path, io=1)
    else:
        print('Latch Up Detection is disabled in the config.')

def run_encoder_power_down(config_path):
    if latch_up_detect_enabled(load_config(config_path)):
        print('Deactivating Latch Up Detection...')
        run_set_latch_up_detect(config_path, io=0)

    print('Deactivating Regulator...')
    run_set_ap(config_path, io=0)

def run_encoder_power(config_path, io):
    if io == 1:
        run_encoder_power_up(config_path)
    else:
        run_encoder_power_down(config_path)

def main():
    print('*** mada_encoder_power.py start ***')

    args = arg_parser()
    try:
        run_encoder_power(args.config, args.io)
    except MadaError as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    print('*** mada_encoder_power.py end ***')

if __name__ == '__main__':
    main()
