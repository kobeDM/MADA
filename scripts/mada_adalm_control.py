#!/usr/bin/env python3

import os
import subprocess
import argparse
import fcntl
import sys
import time

from mada_config import load_config, ConfigError
from mada_adalm_roles import adalm_role

MADAHOME = os.environ['MADAHOME']
ADALM_CTRL = MADAHOME + '/bin/AdalmControl'

def arg_parser():
    parser = argparse.ArgumentParser(description='Reset the counter of ADALM2000.')
    parser.add_argument('-c', '--config', default='MADA_config.json', help='Path to the configuration file (default: MADA_config.json).')
    parser.add_argument('-l', '--latch', type=int, default=1, help='Latch value (default: 1).')
    parser.add_argument('-i', '--idx', type=int, default=0, help='ADALM index (0: DAQ enable, 1: counter reset, 2: software veto).')
    parser.add_argument('-w', '--width', type=float, default=None, help='Output a single latch-up/down pulse of this width in seconds, instead of a static latch.')
    args = parser.parse_args()
    return args

class AdalmError(RuntimeError):
    """Raised when AdalmControl keeps failing after all retries."""


ADALM_LOCK_PATH = MADAHOME + '/run/adalm.lock'

def _run_with_retry(cmd, serial, latch, retries, retry_wait):
    for attempt in range(1, retries + 1):
        ret = subprocess.run(cmd, shell=True).returncode
        if ret == 0:
            return
        print(f'WARNING: AdalmControl failed (code {ret}), attempt {attempt}/{retries}')
        if attempt < retries:
            time.sleep(retry_wait)

    raise AdalmError(f'AdalmControl failed {retries} times for {serial} (latch={latch})')

def run_adalm_control(serial, latch, bg=False, width=None, retries=3, retry_wait=1.0, mask=None, analog=True):
    cmd = ADALM_CTRL + " -s " + serial + " -l " + str(latch)
    if mask is not None:
        cmd += " -m " + hex(mask)
    if not analog:
        cmd += " --no-analog"
    if width is not None:
        cmd += " -w " + str(width)
    print('Execute: ' + cmd)
    if bg:
        return subprocess.Popen(cmd, shell=True)

    # Serialize all callers (threads and processes): two processes opening
    # the same ADALM at once makes the device appear busy or missing.
    with open(ADALM_LOCK_PATH, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _run_with_retry(cmd, serial, latch, retries, retry_wait)

def main():
    args = arg_parser()

    config_path = args.config
    latch = args.latch
    adalm_index = args.idx
    width = args.width

    try:
        serial, mask = adalm_role(load_config(config_path), adalm_index)
    except ConfigError as e:
        print(f'Error: {e}')
        sys.exit(1)

    try:
        run_adalm_control(serial, latch, width=width, mask=mask, analog=(adalm_index != 2))
    except AdalmError as e:
        print(f'Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()