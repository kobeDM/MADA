#!/usr/bin/env python3

import os
import subprocess
from subprocess import PIPE

MADAHOME = os.environ['MADAHOME']
ADALMHOME  = os.environ['ADAHOME']
MADABIN = MADAHOME + '/bin'
ADALMBIN  = ADALMHOME + '/adalm_out/bin'
ADOUT = 'ad_out'
findADALM = "findADALM2000.py"

SN = "1044739614060004160029005f9c48a42b"

def main():
    print('### MADA_conterreset.py start ###')

    cmd = MADABIN + '/' + findADALM + " " + SN
    proc = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
    uri = proc.stdout.decode("utf8").replace("\n", "")
    print("\tURI " + uri + " for S/N: " + SN) 

    cmd = ADALMBIN + "/" + ADOUT + " -u " + uri + " -d 500"
    print('Execute: ' + cmd)
    subprocess.run(cmd, shell=True)

    print('### MADA_conterreset.py end ###')

if __name__ == '__main__':
    main()