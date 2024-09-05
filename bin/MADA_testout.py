#!/usr/bin/env python3

import os
import subprocess
import argparse
import subprocess
from subprocess import PIPE

MADAHOME = os.environ['MADAHOME']
ADAHOME  = os.environ['ADAHOME']
MADABIN  = MADAHOME + '/bin'
ADABIN   = ADAHOME  + '/adalm_out/bin'

findADALM = "findADALM2000.py"

SN = "10447372c6040013f9ff360057ecd401ea"

cmd = MADABIN + '/' + findADALM + " " + SN
proc = subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
URI = proc.stdout.decode("utf8").replace("\n","")
print("\tURI " +URI+ "for S/N: "+SN)      
parser = argparse.ArgumentParser()
parser.add_argument("-u",help="ADALM URI",default=URI)
parser.add_argument("-f",help="test pulse frequency",default=1000,type=int)
parser.add_argument("-d",help="run stop",action='store_true')
args = parser.parse_args( )
URI  = args.u
rate = args.f
d    = args.d

if d:
    cmd = ADABIN + "/ad_out -u " + URI + " -a -v -0. -t 100 " + str(rate)
else:
    cmd = ADABIN + "/ad_out -u " + URI + " -a -v -1. -t 100 -f " + str(rate)
print(cmd)
subprocess.run(cmd, shell=True)
