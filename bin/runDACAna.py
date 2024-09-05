#!/usr/bin/env python3

import os
import subprocess
import argparse

MADAHOME = os.environ['MADAHOME']

MADABIN   = MADAHOME + '/bin'
MADAROOT  = MADAHOME + '/rootmacro'
DACANA    = "DAC_Analysis"
SKEL      = "ShowDAC_skel.cxx"
SHOW_CODE = "ShowDAC.cxx"

def parser():
    argparser=argparse.ArgumentParser()
    argparser.add_argument("DIR",type=str,nargs='?',const=None,help='[dir]')
    argparser.add_argument("Vth",type=str,nargs='?',const=None,help='[V thresholod]')
    argparser.add_argument("-b","--batch", help="batch mode",dest='batch',action="store_true")
    opts=argparser.parse_args()
    return(opts)


def print_and_exe(cmd):
    print("execute:", cmd)
    subprocess.run(cmd,shell=True)


args=parser()
if args.DIR:
    dir=args.DIR
else:
    print('Error: Directory is not selected.')
    exit(1)

if args.Vth:
    Vth=args.Vth
else:
    Vth="8300"
    print('Default Vth is selected:', Vth)

batch_mode=0
if args.batch:
    print("Batch mode")
    batch_mode=1

#analysis
EXECOM = MADABIN + "/" + DACANA + " " + dir + " " + Vth
print("execute:",EXECOM)
subprocess.run(EXECOM, shell=True)

#file moving
files = "DAC.root DAC_ana_config.out base_correct.dac"
cmd = "mv " + files + " " + dir
print_and_exe(cmd)

cmd = "mv Ch*.png " + dir + "/png"
print_and_exe(cmd)

#display
SKEL_FULL = MADAROOT + '/' + SKEL
with open(SKEL_FULL, mode='r') as f:
    str_list = f.readlines()
    showcode = [s.replace("RUNID",dir) for s in str_list]

with open(SHOW_CODE, mode='w') as f:
    f.writelines(showcode)

if batch_mode:
    cmd = 'root -b' + SHOW_CODE
else:
    cmd = 'root ' + SHOW_CODE
    
print_and_exe(cmd)
