#!/usr/bin/python3

import os, sys
import subprocess
import numpy
import glob
import time
import argparse
import json
from subprocess import PIPE

MADAPATH="/home/msgc/miraclue/MADA/bin/"
CONFIGPATH="/home/msgc/miraclue/MADA/config/"

findADALM="findADALM2000.py"
CONFIG="MADA_config.json"
CONFIG_SKEL="MADA_config_SKEL.json"

if(os.path.isfile(CONFIG)):
    print(CONFIG+" exists.")
else:
    # make config file from skelton file
    CONFIG_SKEL=CONFIGPATH+CONFIG_SKEL
    print("\tMADA config slkelton file: "+CONFIG_SKEL)
    skel_open= open(CONFIG_SKEL,'r')
    skel_load = json.load(skel_open)

    #set ADALM URIs by checking S/Ns
    for x in skel_load['ADALM']:
        SN=skel_load['ADALM'][x]['S/N']
        cmd=MADAPATH+findADALM+" "+SN
        proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
        URI=proc.stdout.decode("utf8").replace("\n","")
        print("\tURI in "+CONFIG_SKEL+" "+skel_load['ADALM'][x]['URI']+" for S/N: "+SN)
        skel_load['ADALM'][x]['URI']=URI
        print("\tnew URI in "+CONFIG+" "+skel_load['ADALM'][x]['URI']+" for S/N: "+SN)    
    
        with open(CONFIG, mode='wt', encoding='utf-8') as file:
            json.dump(skel_load, file, ensure_ascii=False, indent=2)

#prepare config file ends.

