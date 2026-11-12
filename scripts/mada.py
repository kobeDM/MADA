#!/usr/bin/env python3

import argparse
import sys

from mada_adalm_roles import daq_roles
from mada_config import load_config, validate_boards, validate_sci, sci_settings, ConfigError
from mada_daemon import daemonize, install_sigterm_handler, remove_pidfile
from mada_daq_session import run_daq
from mada_errors import MadaError
from mada_run_logger import RunLogger


def print_header():
    print('*********************************************************')
    print('*** mada.py                                           ***')
    print('*** Micacle Argon DAQ (http://github.com/kobeDM/MADA) ***')
    print('*** Author      : R.Namai (2026 Apl.)                 ***')
    print('*********************************************************')

def arg_parser():
    parser = argparse.ArgumentParser(description='Micacle Argon DAQ (MADA)')
    parser.add_argument('-c', '--config', help='config file name', default='MADA_config.json')
    parser.add_argument('-f', '--file_num', help='File number in a period', default=512, type=int)
    parser.add_argument('-n', '--event_num', help='Event number in a file', default=1000, type=int)
    parser.add_argument('-d', '--daemon', action='store_true', help='Run in the background, detached from the terminal')
    parser.add_argument('--calin', nargs=2, type=str, help='Calibration input: [IP] [channel (0-127)]', default=None)
    parser.add_argument('--sci', action='store_true', help='SCI mode: an ADALM (the SCI section of the config) records the time of the PMT pulses relative to the DAQ trigger, SCI_NNNN.root in every period directory')
    return parser.parse_args()

def check_config(config_path, sci=False):
    """Fail on the terminal, before daemonizing, if the config cannot run a DAQ."""
    try:
        config = load_config(config_path)
        validate_boards(config)
        daq_roles(config)
        if sci:
            validate_sci(config)
    except ConfigError as e:
        print(f'Error: {e}')
        sys.exit(1)

def main():
    args = arg_parser()
    config_path = args.config
    file_num = args.file_num
    event_num = args.event_num
    calin = args.calin

    check_config(config_path, args.sci)
    sci = sci_settings(load_config(config_path)) if args.sci else None

    # Allocate the starting period before daemonizing, since the per-period
    # log file name (<run_name>_<period>.log) needs to be known up front.
    first_period = RunLogger.new_period()

    if args.daemon:
        daemonize(first_period)

    print_header()
    install_sigterm_handler()

    print('--- Arguments ---')
    print('Config file name : ' + config_path)
    print('File number in a period : ' + str(file_num))
    print('Event number in a file : ' + str(event_num))
    if calin:
        print('Calibration input : IP = ' + calin[0] + ', channel = ' + calin[1])
    if sci:
        print('SCI mode : ADALM ' + sci['S/N'])

    try:
        run_daq(config_path, file_num, event_num, first_period, args.daemon, calin, sci)
    except KeyboardInterrupt:
        print('DAQ stopped by user.')
    except MadaError as e:
        print(f'DAQ stopped due to error: {e}')
        sys.exit(1)
    finally:
        if args.daemon:
            remove_pidfile()

if __name__ == '__main__':
    main()
