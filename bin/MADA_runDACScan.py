#!/usr/bin/env python3

import os
import glob
import argparse

import subprocess

MADAHOME  = os.environ['MADAHOME']

SCAN = MADAHOME + "/bin/DAC_Survey"
ANA = MADAHOME + "/bin/DAC_Analysis"

def parser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("ip", type=str, nargs='?', const=None, help='[IP]', default='192.168.100.64')
    argparser.add_argument("v_th", type=str, nargs='?', const=None, help='[V thresholod]', default=8800)
    args = argparser.parse_args()
    
    return args


def run_command(cmd):
    print("Execute: " + cmd)
    subprocess.run(cmd, shell=True)


def find_newrun():
    dir_header = 'DAC_run'
    files = glob.glob(dir_header + '*')
    if len(files) == 0:
        newrun = dir_header + '0'.zfill(4)
    else:
        files.sort(reverse=True)
        num_pos = files[0].find("run")
        newrun = dir_header + str(int(files[0][num_pos + 3:num_pos + 3 + 4]) + 1).zfill(4)
    
    return newrun


def main():
    print('### MADA_runDACScan.py start ###')

    args = parser()
    ip = args.ip
    Vth = args.v_th

    newrun = find_newrun()
    cmd = "mkdir " + newrun
    run_command(cmd)

    os.chdir(newrun)

    cmd = "mkdir png"
    run_command(cmd)

    cmd = SCAN + " " + ip + " " + Vth
    run_command(cmd)

    os.chdir("../")

    cmd = ANA + " " + newrun + "/ " + Vth
    run_command(cmd)

    cmd = "mv Ch_*.png " + newrun + "/png"
    run_command(cmd)
    
    cmd = "mv DAC.root " + newrun
    run_command(cmd)

    cmd = "mv base_correct.dac " + newrun
    run_command(cmd)

    cmd = "mv DACsurvey_config.out DAC_ana_config.out " + newrun
    run_command(cmd)

    print('### MADA_runDACScan.py start ###')


if __name__ == '__main__':
    main()
