#!/usr/bin/python3

import subprocess
import argparse

ADAPATH="/home/msgc/adalm/adalm_out"
import subprocess
URI="usb:1.15.5"

parser = argparse.ArgumentParser()
parser.add_argument("-f",help="test pulse frequency",default=1000,type=int)
parser.add_argument("-u",help="ADALM URI",default=URI)
args = parser.parse_args( )
rate=args.f
URI=args.u

com=ADAPATH+"/bin/ad_out -u "+URI+" -a -v -1. -t 100 -f "+str(rate)
print(com)
subprocess.run(com,shell=True)
