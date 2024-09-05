#!/usr/bin/env python3

import os
import subprocess
import subprocess
from subprocess import PIPE

MADAHOME = os.environ['MADAHOME']
ADAHOME  = os.environ['ADAHOME']
MADABIN  = MADAHOME + '/bin'
ADAOUT   = ADAHOME + '/adalm_out'
findADALM = "findADALM2000.py"

SN = "1044739614060004160029005f9c48a42b"

cmd = MADABIN + '/' + findADALM + " " + SN
proc = subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
URI = proc.stdout.decode("utf8").replace("\n","")
print("\tURI " +URI+ "for S/N: "+SN) 

# disable = 0
# parser = argparse.ArgumentParser()
# parser.add_argument("-u",help="ADALM URI",default=URI)
# args = parser.parse_args( )
# URI = args.u
cmd = ADAOUT + "/bin/ad_out -u " + URI + " -d 500"
print(cmd)
subprocess.run(cmd,shell=True)

