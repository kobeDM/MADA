#!/usr/bin/env python3

import argparse
import sys

from mada_config import load_config, ConfigError
from mada_adalm_roles import adalm_role, ROLE_VETO
from mada_adalm_runner import run_adalm_control, AdalmError


def arg_parser():
    parser = argparse.ArgumentParser(description='Set the DIO lines of one ADALM2000 role (DAQ enable, counter reset, software veto).')
    parser.add_argument('-c', '--config', default='MADA_config.json', help='Path to the configuration file (default: MADA_config.json).')
    parser.add_argument('-l', '--latch', type=int, default=1, help='Latch value (default: 1).')
    parser.add_argument('-i', '--idx', type=int, default=0, help='ADALM index (0: DAQ enable, 1: counter reset, 2: software veto).')
    parser.add_argument('-w', '--width', type=float, default=None, help='Output a single latch-up/down pulse of this width in seconds, instead of a static latch.')
    return parser.parse_args()


def main():
    args = arg_parser()

    try:
        serial, mask = adalm_role(load_config(args.config), args.idx)
        run_adalm_control(serial, args.latch, width=args.width, mask=mask, analog=(args.idx != ROLE_VETO))
    except (ConfigError, AdalmError) as e:
        print(f'Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
