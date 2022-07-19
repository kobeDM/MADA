#!/usr/bin/python3
import subprocess, os,sys
import argparse
import glob
from subprocess import PIPE

EXEPATH="/home/msgc/miraclue/ana/bin"
EXE="DAC_Analysis"
SKEL="ShowDAC_skel.cxx"
SHOW_CODE="ShowDAC.cxx"

def parser():
    argparser=argparse.ArgumentParser()
    argparser.add_argument("DIR",type=str,nargs='?',const=None,help='[dir]')
    argparser.add_argument("Vth",type=str,nargs='?',const=None,help='[V thresholod]')
    argparser.add_argument("-b","--batch", help="batch mode",dest='batch',action="store_true")
    opts=argparser.parse_args()
    return(opts)


def p_and_e(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd,shell=True)


#def find_newrun(dir_name):
#    data_header = 'run'
#    files = glob.glob(dir_name+'*')
#    if len(files) == 0:
#        return data_header+'0'.zfill(4)
#    else:
#        files.sort(reverse=True)
#        num_pos = files[0].find('run')
#        return data_header+str(int(files[0][num_pos+3:num_pos+3+4])+1).zfill(4)


args=parser()
if(args.DIR):
    run=args.DIR
else:
    run="DAC_run0000"

if(args.Vth):
    Vth=args.Vth
else:
    Vth="8300"
if args.batch:
    #switch for batch mode
    print("batch mode")
    batch_mode=1
else:
    batch_mode=0

#analysis
EXECOM=EXEPATH+"/"+EXE+" "+run+" "+Vth
print("execute:",EXECOM)
subprocess.run(EXECOM,shell=True)

#file moving
files="DAC.root DAC_ana_config.out base_correct.dac"
COM="mv "+files+" "+run
p_and_e(COM)
#subprocess.run(COM,shell=True)

COM="mv Ch*.png "+run+"/png"
#subprocess.run(COM,shell=True)
p_and_e(COM)

#display
SKEL_FULL=EXEPATH+'/'+SKEL
with open(SKEL_FULL, mode='r') as f:
    str_list = f.readlines()
    showcode = [ s.replace("RUNID",run) for s in str_list ]

with open(SHOW_CODE, mode='w') as f:
    f.writelines(showcode)

if batch_mode:
    CMD='root -b'+SHOW_CODE
else:
    CMD='root '+SHOW_CODE
    
p_and_e(CMD)
