#!/usr/bin/python3
import subprocess
import os
import sys
import argparse
import glob
from subprocess import PIPE

MADAPATH = "/home/msgc/miraclue/MADA/bin"
EXE = "MADA_DACScan"
# ANAPATH="/home/msgc/miraclue/ana/bin"
ANA = "MADA_DACAna"


def parser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("IP", type=str, nargs='?', const=None, help='[IP]')
    argparser.add_argument("Vth", type=str, nargs='?', const=None, help='[V thresholod]')
    opts = argparser.parse_args()
    return (opts)


def print_and_exe(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd, shell=True)


def find_newrun():
    dir_header = 'DAC_run'
    files = glob.glob(dir_header+'*')
    if len(files) == 0:
        return dir_header+'0'.zfill(4)
    else:
        files.sort(reverse=True)
#        num_pos = files[0].find(dir_header)
        num_pos = files[0].find("run")
        # print(files)
        # print("num_pos",num_pos)
        return dir_header+str(int(files[0][num_pos+3:num_pos+3+4])+1).zfill(4)


# if(len(sys.argv)<2):
#    print("runDACScan IP [Vth]")
#    sys.exit(1)

args = parser()
if (args.IP):
    IP = args.IP
else:
    print("runDACScan.py IP [Vth]")
    sys.exit(1)
#    IP="192.168.100.25"

if (args.Vth):
    Vth = args.Vth
else:
    Vth = "8800"


# IP="192.168.100.25"
# VthLow="0"
# Vth="8800"
# VthLow="6000"
# VthHigh="8900"
# VthHigh="16383" #for full-range scan
# VthStep="1000"
# VthStep="64"

newrun = find_newrun()
CMD = "mkdir "+newrun
print_and_exe(CMD)
# subprocess.run(CMD,shell=True)
os.chdir(newrun)
CMD = "mkdir png"
print_and_exe(CMD)

EXECOM = MADAPATH+"/"+EXE+" "+IP+" "+Vth
print_and_exe(EXECOM)
os.chdir("../")
# print("execute:",EXECOM)
# subprocess.run(EXECOM,shell=True)

#CMD="mv *.png png"
# print_and_exe(CMD)

# print(ANAPATH)
# print(ANA)
CMD = MADAPATH+"/"+ANA+" "+newrun+" "+Vth
print_and_exe(CMD)


COM = "mv DAC.root "+newrun
print_and_exe(COM)


COM = "mv base_correct.dac "+newrun
print_and_exe(COM)
