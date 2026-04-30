#!/usr/bin/env python3

import os
import subprocess
import argparse
import subprocess
from subprocess import PIPE

MADAHOME  = os.environ['MADAHOME']

ADSW  = os.environ['ADSW']
ADOUT = ADSW + '/bin/ad_out'

# scripts
findADALM = MADAHOME + "/bin/findADALM2000.py"

SN = "10447384b904001612002500df1edb6193" # ADALM S/N for DAQ enable

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--uri", help="ADALM URI")
    parser.add_argument("-d", "--disable", help="disable"  , action='store_true')
    args = parser.parse_args()

    return args

def main():
    print('### MADA_DAQenable.py start ###')
    
    args = parser()
    
    if args.uri:
        uri = args.uri
    else:
        cmd  = findADALM + " " + SN
        proc = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
        uri  = proc.stdout.decode("utf8").replace("\n", "")
        print("URI", uri, "for S/N:", SN)

    if args.disable: # latching down
        cmd = ADOUT + " -u " + uri + " -m"
    else: # latching up
        cmd = ADOUT + " -u " + uri + " -l"

    print('Execute:', cmd)
    subprocess.run(cmd, shell=True)

    print('### MADA_DAQenable.py end ###')

if __name__ == '__main__':
    main()