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
    argparser = argparse.ArgumentParser()
    argparser.add_argument("dir", type=str, nargs='?', const=None, help='[dir]')
    argparser.add_argument("vth", type=str, nargs='?', const=None, help='[V thresholod]')
    argparser.add_argument("-b", "--batch", help="batch mode", dest='batch', action="store_true")
    args = argparser.parse_args()
    return args

def print_and_exe(cmd):
    print("Execute: " + cmd)
    subprocess.run(cmd, shell=True)

def main():
    args = parser()
    if args.dir:
        dir=args.dir
    else:
        print('Error: Directory is not selected.')
        exit(1)

    if args.vth:
        vth=args.vth
    else:
        vth="8300"
        print('Default Vth is selected:', vth)

    batch_mode=0
    if args.batch:
        print("Batch mode")
        batch_mode=1

    #analysis
    EXECOM = MADABIN + "/" + DACANA + " " + dir + " " + vth
    print("Execute: " + EXECOM)
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

if __name__ == '__main__':
    main()