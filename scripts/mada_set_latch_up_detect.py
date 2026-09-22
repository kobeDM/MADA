#!/usr/bin/env python3

import os
import sys
import json
import subprocess
import argparse

MADAHOME = os.environ['MADAHOME']
MADABIN = MADAHOME + '/bin'

FETCHCONFIG = os.path.join(MADABIN, 'mada_fetch_config.py')
SETLATCHUPDETECT = os.path.join(MADABIN, 'SetLatchUpDetect')

CONFIG = './MADA_config.json'


class SetLatchUpDetectError(RuntimeError):
    """Raised when SetLatchUpDetect gets no reply from one or more boards."""


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('io', help='0/1')
    parser.add_argument('-c', '--config', default=CONFIG)
    args = parser.parse_args()
    return args


def run_set_latch_up_detect(config_path: str, io : int):
    with open(config_path, 'r') as file:
        config_load = json.load(file)

    targets = [
        (name, data['IP'])
        for name, data in config_load.get('gigaIwaki', {}).items()
        if data.get('active') == 1
    ]

    # Launch every board's SetLatchUpDetect first so the commands go out
    # together, then collect results, rather than waiting on each in turn.
    procs = {}
    for name, ip in targets:
        print('GigaIwaki: ' + name)
        print('  IP      : ' + ip)
        print('  IO      : ' + str(io))

        cmd = [SETLATCHUPDETECT, ip, str(io)]
        print('Execute : ' + ' '.join(cmd))
        procs[name] = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    failed = []
    for name, proc in procs.items():
        stdout, _ = proc.communicate()
        print(stdout)
        print('---')
        if proc.returncode != 0:
            failed.append(name)

    if failed:
        raise SetLatchUpDetectError(f'SetLatchUpDetect got no reply from: {", ".join(failed)}')

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

    try:
        run_set_latch_up_detect(config, io)
    except SetLatchUpDetectError as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    print("*** mada_set_latch_up_detect.py end ***")

if __name__ == "__main__":
    main()