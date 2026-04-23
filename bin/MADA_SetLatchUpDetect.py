#!/usr/bin/env python3

import os
import subprocess
import argparse

MADAHOME = os.environ['MADAHOME']
MADABIN = MADAHOME + '/bin'

SETLATCHUPDETECT = MADABIN + "/SetLatchUpDetect"

def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("ip")
    parser.add_argument("io")
    args = parser.parse_args()
    return args

def main():
    args = arg_parser()

    print("*** MADA_SetLatchUpDetect.py start ***")

    cmd = [SETLATCHUPDETECT, args.ip, args.io]
    print(cmd)
    stdout = subprocess.run(cmd, capture_output=True, text=True).stdout
    print(stdout)

    print("*** MADA_SetLatchUpDetect.py end ***")

if __name__ == "__main__":
    main()