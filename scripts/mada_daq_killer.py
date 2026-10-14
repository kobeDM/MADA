#!/usr/bin/env python3

"""Close the file that was being acquired when the DAQ stopped (end time and
size into the .info files, rate log) and stop the readers."""

import argparse
import sys
import time

from mada_config import load_config, active_boards
from mada_errors import MadaError
from mada_process import stop_processes
from mada_run_logger import RunLogger

CONFIG = "MADA_config.json"


def arg_parser():
    parser = argparse.ArgumentParser(description='Finalize the latest DAQ file and stop its readers.')
    parser.add_argument("-c", "--config", help="config file name", default=CONFIG)
    return parser.parse_args()


def finalize_latest_file(config_path):
    boards = active_boards(load_config(config_path))
    logger = RunLogger.latest(config_path)
    if logger is None:
        print('No period directory found; nothing to finalize.')
        return

    file_id = logger.latest_file_id()
    if file_id < 0:
        print(f'No info file in period {logger.period_id}; nothing to finalize.')
        return

    logger.finalize_file(file_id, boards, time.time())


def run_daq_killer(config_path=CONFIG):
    # Always stop the readers, even if finalizing the files fails.
    try:
        finalize_latest_file(config_path)
    finally:
        stop_processes(['MadaIwaki'], 'MadaIwaki processes')


def main():
    try:
        run_daq_killer(arg_parser().config)
    except MadaError as e:
        print(f'ERROR: {e}')
        sys.exit(1)


if __name__ == "__main__":
    main()
