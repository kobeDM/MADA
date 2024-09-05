#!/usr/bin/env python3
import subprocess, os,sys
import argparse
import glob
from subprocess import PIPE

print('### MADA_runVthScan.py start ###')

def parser():
    argparser=argparse.ArgumentParser()
    argparser.add_argument("IP",type=str,nargs='?',const=None,help='[IP]')
    argparser.add_argument("VthLow",type=int,nargs='?',const=None,help='[V thresholod lower bound]')
    argparser.add_argument("VthHigh",type=int,nargs='?',const=None,help='[V thresholod upper bound]')
    argparser.add_argument("VthStep",type=int,nargs='?',const=None,help='[V thresholod step]')
    argparser.add_argument("-b","--batch", help="batch mode",dest='batch',action="store_true")
    opts=argparser.parse_args()
    return(opts)

def print_and_exe(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd,shell=True)

def find_newrun():
    dir_header = 'Vth_run'
    files = glob.glob(dir_header+'*')
    if len(files) == 0:
        return dir_header+'0'.zfill(4)
    else:
        files.sort(reverse=True)
        num_pos = files[0].find("run")
        return dir_header+str(int(files[0][num_pos+3:num_pos+3+4])+1).zfill(4)


MADAHOME    = os.environ["MADAHOME"]
MADABIN     = MADAHOME + '/bin/'
CONFIGPATH  = MADAHOME + "/config/"
DACFILEPATH = "/home/msgc/namai/VthScan/archive/DACfile/"

FETCHCON   = MADABIN + "MADA_fetch_config.py"
EXE_SETDAC = MADABIN + "SetDAC"
EXE_DAQ    = MADABIN + "MADA_VthScan"
EXE_ANA    = MADABIN + "MADA_runVthAna.py"

DACfile = DACFILEPATH + "192.168.100.19_20.dac"
# DACfile = DACFILEPATH + "192.168.100.25_9.dac"
# DACfile = "/home/msgc/namai/VthScan/DAC_run0037/base_correct.dac"

# default setting
VthLow     = "0"
VthHigh    = "16384"
VthStep    = "32"
batch_mode = 0

args=parser()
if args.IP:
    IP=args.IP
else:
    print("runDACScan [IP] [Vth lower] [Vth upper] [Vth step]")
    sys.exit(1)

cmd = FETCHCON
ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
print(ret.stdout)        

# write null DAC velues
cmd = EXE_SETDAC + " " + IP + " " + DACfile
print_and_exe(cmd)


if args.VthLow:
    VthLow = args.VthLow
else:
    print('Used default VthLow:', VthLow)

if args.VthHigh:
    VthHigh=args.VthHigh
else:
    print('Used default VthHigh:', VthHigh)

if args.VthStep:
    VthStep=args.VthStep
else:
    print('Used default VthStep:', VthStep)

if args.batch:
    print("Batch mode")
    batch_mode = 1


print("IP      :", IP     )
print("Vth Low :", VthLow )
print("Vth High:", VthHigh)
print("Vth Step:", VthStep)


# cmd="pwd".split('/')
# subprocess.run(cmd,shell=True)
    
newrun = find_newrun()
cmd = "mkdir " + newrun
print_and_exe(cmd)

os.chdir(newrun)
cmd = EXE_DAQ + " " + IP + " " + str(VthLow) + " "+str(VthHigh) + " "+str(VthStep)
print_and_exe(cmd)
os.chdir("../")

if batch_mode:
    cmd = EXE_ANA + " -b " + newrun
else:
    cmd = EXE_ANA + " " + newrun
print_and_exe(cmd)

cmd = "mv Vthcheck.png " + newrun
print_and_exe(cmd)

print('### MADA_runVthScan.py end ###')
