#!/usr/bin/env python3

import os
import subprocess
import argparse
import subprocess
from subprocess import PIPE

MADAHOME = os.environ['MADAHOME']
ADALMHOME  = os.environ['ADAHOME']
MADABIN  = MADAHOME + '/bin'
ADALMBIN   = ADALMHOME  + '/adalm_out/bin'

findADALM = "findADALM2000.py"

SN = "10447372c6040013f9ff360057ecd401ea"

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--uri", help="ADALM URI")
    parser.add_argument("-f", "--freq", help="test pulse frequency", default=1000, type=int)
    parser.add_argument("-d", "--disable", help="run stop", action='store_true')
    args = parser.parse_args()

    return args

def main():
    args = parser()
    if args.uri:
        uri = args.uri
    else:
        cmd = MADABIN + '/' + findADALM + " " + SN
        proc = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
        uri = proc.stdout.decode("utf8").replace("\n", "")
        print("\tURI " + uri + " for S/N: " + SN)      

    rate = args.freq
    if args.disable:
        cmd = ADALMBIN + "/ad_out -u " + uri + " -a -v -0. -t 100 " + str(rate)
    else:
        cmd = ADALMBIN + "/ad_out -u " + uri + " -a -v -1. -t 100 -f " + str(rate)
    
    print('Execute: ' + cmd)
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    main()
