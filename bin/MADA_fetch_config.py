#!/usr/bin/env python3

import os, sys
import subprocess
import numpy
import glob
import time
import argparse
import json
from subprocess import PIPE

print('### MADA_fetch_config.py start ###')

MADAPATH   = '/home/msgc/miraclue/MADA'
BINPATH    = MADAPATH + '/bin'
CONFIGPATH = MADAPATH + '/config'

findADALM   = 'findADALM2000.py'
CONFIG      = 'MADA_config.json'
CONFIG_SKEL = 'MADA_config_SKEL.json'

if os.path.isfile(CONFIG):
    print(CONFIG, 'exists.')
else:
    # make config file from skelton file
    CONFIG_SKEL = CONFIGPATH + '/' + CONFIG_SKEL
    print('MADA config slkelton file:', CONFIG_SKEL)
    skel_open = open(CONFIG_SKEL, 'r')
    skel_load = json.load(skel_open)

    #set ADALM URIs by checking S/Ns
    for x in skel_load['ADALM']:
        SN = skel_load['ADALM'][x]['S/N']
        cmd = BINPATH + '/' + findADALM + ' ' + SN
        # print('Execute:', cmd)
        ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None,  check=False, capture_output=False)
        # print(ret.stdout)
        
        URI = ret.stdout.decode('utf8').replace('\n','')
        skel_load['ADALM'][x]['URI'] = URI
        print('\tS/N:', SN, '-->', skel_load['ADALM'][x]['URI'])    
    
        with open(CONFIG, mode='wt', encoding='utf-8') as file:
            json.dump(skel_load, file, ensure_ascii=False, indent=4)

print('### MADA_fetch_config.py end ###')