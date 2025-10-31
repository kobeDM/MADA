#!/usr/bin/env python3

import os
import subprocess
import argparse
import subprocess
from subprocess import PIPE

MADAHOME  = os.environ['MADAHOME']
MADABIN   = MADAHOME + '/bin/'
ADALMHOME  = os.environ['ADAHOME']
ADALMOUT = ADALMHOME + '/adalm_out'

# scripts
findADALM = "findADALM2000.py"

# SN="104473961406000712000e0056e64887db"
# SN="10447384b904001612002500df1edb6193"
SN = "10447372c6040013f9ff360057ecd401ea" # ADALM S/N for DAQ enable

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
        cmd  = MADABIN + '/' + findADALM + " " + SN
        proc = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
        uri  = proc.stdout.decode("utf8").replace("\n", "")
        print("URI", uri, "for S/N:", SN)

    if args.disable: # latching down
        cmd = ADALMOUT + "/bin/ad_out -u " + uri + " -m"
    else: # latching up
        cmd = ADALMOUT + "/bin/ad_out -u " + uri + " -l"

    print('Execute:', cmd)
    subprocess.run(cmd, shell=True)

    print('### MADA_DAQenable.py end ###')

if __name__ == '__main__':
    main()