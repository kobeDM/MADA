#!/usr/bin/env python3
import subprocess, os,sys
import argparse
import glob
from subprocess import PIPE

MADAHOME  = os.environ['MADAHOME']
IWAKIANAHOME = os.environ['IWAKIANAHOME']

MADABIN = MADAHOME + '/bin'
IWAKIANABIN = IWAKIANAHOME + '/bin'
# SCAN = "MADA_DACScan"
SCAN = "DAC_Survey"
# ANA = "MADA_DACAna"
ANA = "DAC_Analysis"

def parser():
    argparser=argparse.ArgumentParser()
    argparser.add_argument("IP",type=str,nargs='?',const=None,help='[IP]')
    argparser.add_argument("Vth",type=str,nargs='?',const=None,help='[V thresholod]')
    opts=argparser.parse_args()
    return(opts)

def print_and_exe(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd,shell=True)

def find_newrun():
    dir_header = 'DAC_run'
    files = glob.glob(dir_header+'*')
    if len(files) == 0:
        return dir_header+'0'.zfill(4)
    else:
        files.sort(reverse=True)
        num_pos = files[0].find("run")
        return dir_header+str(int(files[0][num_pos+3:num_pos+3+4])+1).zfill(4)

args=parser()
if args.IP:
    IP=args.IP
else:
    print("runDACScan.py IP [Vth]")
    sys.exit(1)

if args.Vth:
    Vth=args.Vth
else:
    Vth="8800"
    print('Used default Vth:', Vth)


newrun = find_newrun()
cmd = "mkdir " + newrun
print_and_exe(cmd)

os.chdir(newrun)

cmd = "mkdir png"
print_and_exe(cmd)

# cmd = MADABIN + "/" + SCAN + " " + IP + " " + Vth
# cmd = "/home/msgc/miraclue/Analysis_program/bin/DAC_Survey" + " " + IP + " " + Vth
cmd = IWAKIANABIN + "/" + SCAN + " " + IP + " " + Vth
print_and_exe(cmd)

os.chdir("../")

# cmd = MADABIN + "/" + ANA + " " + newrun + " " + Vth
# cmd = "/home/msgc/miraclue/Analysis_program/bin/DAC_Analysis" + " " + newrun + "/ " + Vth
cmd = IWAKIANABIN + "/" + ANA + " " + newrun + " " + Vth
print_and_exe(cmd)
  
cmd = "mv DAC.root " + newrun 
print_and_exe(cmd)

cmd = "mv base_correct.dac " + newrun
print_and_exe(cmd)
