#!/usr/bin/env python3

import subprocess
import argparse
import subprocess
from subprocess import PIPE

print('### MADA_DAQenable.py start ###')

MADAPATH = "/home/msgc/miraclue/MADA/bin"
ADAPATH  = "/home/msgc/adalm/adalm_out"

# scripts
FETCHCON  = "MADA_fetch_config.py"
findADALM = "findADALM2000.py"
SETDAC    = "MADA_SetAllDACs.py"

# configs
CONFIG      = "MADA_config.json"
CONFIG_SKEL = "MADA_config_SKEL.json"

# URI="usb:1.7.5"
# SN="104473961406000712000e0056e64887db"
# SN="10447384b904001612002500df1edb6193"
SN = "10447372c6040013f9ff360057ecd401ea" #  ADALM S/N for DAQ enable

cmd  = MADAPATH + '/' + findADALM + " " + SN
proc = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
URI  = proc.stdout.decode("utf8").replace("\n","")
print("\tURI", URI, "for S/N:", SN)
disable = 0

parser = argparse.ArgumentParser()
parser.add_argument("-d", help="disable"  , action='store_true')
parser.add_argument("-u", help="ADALM URI", default=URI        )
args = parser.parse_args()
URI     = args.u
disable = args.d

if disable: # latching down
    cmd = ADAPATH + "/bin/ad_out -u " + URI + " -m"
else:
    cmd = ADAPATH + "/bin/ad_out -u " + URI + " -l"

print('Execute:', cmd)
subprocess.run(cmd, shell=True)

print('### MADA_DAQenable.py end ###')
