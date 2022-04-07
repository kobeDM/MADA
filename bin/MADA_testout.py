#!/usr/bin/python3

import subprocess
import argparse


import subprocess
from subprocess import PIPE

MADAPATH="/home/msgc/miraclue/MADA/bin/"
ADAPATH="/home/msgc/adalm/adalm_out"
findADALM="findADALM2000.py"

#configs
CONFIG="MADA_config.json"
CONFIG_SKEL="MADA_config_SKEL.json"

#URI="usb:1.7.5"
SN="104473961406000712000e0056e64887db"

cmd=MADAPATH+findADALM+" "+SN
proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
URI=proc.stdout.decode("utf8").replace("\n","")
d=0
print("\tURI " +URI+ "for S/N: "+SN)      
parser = argparse.ArgumentParser()
parser.add_argument("-d",help="run stop",action='store_true')
parser.add_argument("-f",help="test pulse frequency",default=1000,type=int)
parser.add_argument("-u",help="ADALM URI",default=URI)
args = parser.parse_args( )
rate=args.f
URI=args.u
d=args.d

if d:
    com=ADAPATH+"/bin/ad_out -u "+URI+" -a -v -0. -t 100 "+str(rate)
else:
    com=ADAPATH+"/bin/ad_out -u "+URI+" -a -v -1. -t 100 -f "+str(rate)
print(com)
subprocess.run(com,shell=True)
