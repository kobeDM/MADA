#!/usr/bin/env python3

import os
import sys
import json
import subprocess
import argparse

MADAHOME = os.environ['MADAHOME']
MADABIN = MADAHOME + '/bin'

SETAP = os.path.join(MADABIN, 'SetAP')

CONFIG = './MADA_config.json'


class SetApError(RuntimeError):
    """Raised when SetAP gets no reply from one or more boards."""


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('io', type=int, choices=[0, 1], help='0/1')
    parser.add_argument('-c', '--config', default=CONFIG)
    args = parser.parse_args()
    return args

def run_set_ap(config_path, io, target_ip=None):
    with open(config_path, 'r') as file:
        config_load = json.load(file)

    targets = []
    for name, data in config_load.get('gigaIwaki', {}).items():
        if data.get('active') != 1:
            continue

        ip = data.get('IP')
        if target_ip and ip != target_ip:
            continue

        targets.append((name, ip))

    # Launch every board's SetAP first so the commands go out together,
    # then collect results, rather than waiting on each board in turn.
    procs = {}
    for name, ip in targets:
        print('GigaIwaki: ' + name)
        print('  IP      : ' + ip)
        print('  IO      : ' + str(io))

        cmd = [SETAP, ip, str(io)]
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
        raise SetApError(f'SetAP got no reply from: {", ".join(failed)}')

def main():
    print("*** mada_set_ap.py start ***")

    args = arg_parser()
    io = args.io
    config = args.config

    try:
        run_set_ap(config, io)
    except SetApError as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    print("*** mada_set_ap.py end ***")

if __name__ == "__main__":
    main()