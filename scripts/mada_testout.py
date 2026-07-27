#!/usr/bin/env python3

import os
import subprocess
import argparse

MADAHOME = os.environ['MADAHOME']
OUTPUT_TEST_PULSE = MADAHOME + "/bin/OutputTestPulse"

SN = "10447372c6040013f9ff360057ecd401ea"

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--serial", help="ADALM serial number", default=SN)
    parser.add_argument("-v", "--voltage", help="output voltage (V)", default=3.3, type=float)
    parser.add_argument("-f", "--freq", help="test pulse frequency (Hz)", default=1000, type=int)
    parser.add_argument("-d", "--disable", help="stop output", action='store_true')
    args = parser.parse_args()

    return args

def main():
    args = parser()
    io = 0 if args.disable else 1

    cmd = [OUTPUT_TEST_PULSE, args.serial, str(io), str(args.voltage), str(args.freq)]
    print('Execute: ' + ' '.join(cmd))
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
