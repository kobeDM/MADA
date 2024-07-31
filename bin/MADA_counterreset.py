#!/usr/bin/python3

import subprocess
import argparse
import subprocess
from subprocess import PIPE

MADAPATH="/home/msgc/miraclue/MADA/bin/"
ADAPATH="/home/msgc/adalm/adalm_out"

#scripts
FETCHCON="MADA_fetch_config.py"
findADALM="findADALM2000.py"
SETDAC="MADA_SetAllDACs.py"

#configs
CONFIG="MADA_config.json"
CONFIG_SKEL="MADA_config_SKEL.json"

#def getURI

#URI="usb:1.7.5"
SN="1044739614060004160029005f9c48a42b"
#SN="104473961406000b03003800c90049e980"
#SN="10447372c6040013f9ff360057ecd401ea"
#SN="104473961406000712000e0056e64887db"
#SN="10447384b904001612002500df1edb6193"
cmd=MADAPATH+findADALM+" "+SN
proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
URI=proc.stdout.decode("utf8").replace("\n","")
print("\tURI " +URI+ "for S/N: "+SN)      
disable=0;
parser = argparse.ArgumentParser()
#parser.add_argument("-d",help="disable",action='store_true')
parser.add_argument("-u",help="ADALM URI",default=URI)
args = parser.parse_args( )
#rate=args.f
URI=args.u
#disable=args.d
#if disable: # latching down
#    com=ADAPATH+"/bin/ad_out -u "+URI+" -d"
#else:
#    com=ADAPATH+"/bin/ad_out -u "+URI+" -l"
com=ADAPATH+"/bin/ad_out -u "+URI+" -d 500"
print(com)
subprocess.run(com,shell=True)

