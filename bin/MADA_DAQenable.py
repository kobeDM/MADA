#!/usr/bin/python3

import argparse
import subprocess
from subprocess import PIPE

MADAPATH = "/home/msgc/miraclue/MADA/bin/"
ADAPATH = "/home/msgc/adalm/adalm_out"

# scripts
FETCHCON = "MADA_fetch_config.py"
findADALM = "findADALM2000.py"
SETDAC = "MADA_SetAllDACs.py"

# configs
CONFIG = "MADA_config.json"
CONFIG_SKEL = "MADA_config_SKEL.json"

SN = "10447384b904001612002500df1edb6193"  # adalm0
cmd = MADAPATH+findADALM+" "+SN
proc = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
URI = proc.stdout.decode("utf8").replace("\n", "")
print("\tURI " + URI + "for S/N: "+SN)

disable = 0
parser = argparse.ArgumentParser()
parser.add_argument("-d", help="disable", action='store_true')
parser.add_argument("-u", help="ADALM URI", default=URI)
args = parser.parse_args()
URI = args.u
disable = args.d
if disable:  # latching down
    com = ADAPATH+"/bin/ad_out -u "+URI+" -m"
else:
    com = ADAPATH+"/bin/ad_out -u "+URI+" -l"

print(com)
subprocess.run(com, shell=True)
