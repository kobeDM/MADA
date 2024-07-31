#!/usr/bin/env python3

import os, sys

import subprocess
from subprocess import PIPE

import numpy
import glob
import time
import argparse

ADALMPATH = '/home/msgc/adalm/adalm_out/bin/'
ADOUT     = 'ad_out'

productID = '0456:b672'

targetSN = ''
if len(sys.argv) == 1:
    find = 0
else:
    targetSN = sys.argv[1]
    find = 1

# Search ADALM2000 from product ID
cmd = 'iio_attr -a -C fw_version | grep ' + productID
# print('Execute:', cmd)
ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=PIPE, text=True)
devices = ret.stderr.split('0456')
numdev = len(devices) - 1

usbs = []
SN   = []
for dev in range(numdev):
    SN.append(devices[dev+1].split()[6].split('=')[1])
    usbs.append(devices[dev+1].split()[7].split(':')[1].replace(']',''))

# Check devices
found = 0
for i in range(len(usbs)):
    cmd = ADALMPATH + ADOUT + ' -s -u ' + usbs[i] + '| grep serial'
    # print('Execute:', cmd)
    ret = subprocess.run(cmd, shell=True, stdout=PIPE, text=True)
    if find == 0:
        print('device', str(i), '\t', usbs[i], '\t S/N:', SN[i])
    elif find == 1:
        if SN[i] == targetSN:
            print('usb:', usbs[i])
            found += 1

if find and not found:
    print('No device with S/N ', targetSN, 'found.')
    
