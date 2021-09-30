#!/usr/bin/python3
import subprocess, os,sys
import argparse
import glob
from subprocess import PIPE

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

MADAPATH="/home/msgc/miraclue/MADA/bin/"
CONFIGPATH="/home/msgc/miraclue/MADA/config/"

VTHSCAN="MADA_VthScan"
EXE_SETDAC=MADAPATH+"SetDAC"
EXE_DAQ=MADAPATH+"MADA_VthScan"
EXE_ANA=MADAPATH+"MADA_runVthAna.py"



args=parser()
if(args.IP):
    IP=args.IP
else:
    print("runDACScan IP [Vth lower] [Vth upper] [Vth step]")
    sys.exit(1)
#    IP="192.168.100.25"

#write null DAC velues
#DACfile=CONFIGPATH+"base_correct_null.dac"
#cmd=EXE_SETDAC+" "+IP+" "+DACfile
#print_and_exe(cmd)


if(args.VthLow):
    VthLow=args.VthLow
else:
    #VthLow="8500"
    VthLow="0"

if(args.VthHigh):
    VthHigh=args.VthHigh
else:
#    VthHigh="8900"
    VthHigh="16384"

if(args.VthStep):
    VthStep=args.VthStep
else:
    #VthStep="1000"
    #VthStep="64"
    VthStep="32"

if args.batch:
    #switch for batch mode
    print("batch mode")
    batch_mode=1
else:
    batch_mode=0

print("IP:",IP)
print("Vth low:",VthLow)
print("Vth high:",VthHigh)
print("Vth Step:",VthStep)
if batch_mode:
    print("batch mode")

cmd="pwd".split('/')
subprocess.run(cmd,shell=True)

    
newrun=find_newrun()
CMD="mkdir "+newrun
print_and_exe(CMD)
#subprocess.run(CMD,shell=True)
os.chdir(newrun)

#EXECOM=EXEPATH+"/"+EXE+" "+IP+" "+srt(VthLow)+" "+srt(VthHigh)+" "+srt(VthStep)
CMD=EXE_DAQ+" "+IP+" "+str(VthLow)+" "+str(VthHigh)+" "+str(VthStep)
print_and_exe(CMD)

os.chdir("../")


if batch_mode:
    CMD=EXE_ANA+" -b "+newrun
else:
    CMD=EXE_ANA+" "+newrun

print_and_exe(CMD)


#CMD="mv scan_config.out Vth.root"+
#print("execute:",EXECOM)
#subprocess.run(EXECOM,shell=True)


