#!/usr/bin/python3
import subprocess, os,sys
import argparse
import json
import datetime

MADAPATH="/home/msgc/miraclue/MADA/bin/"
CONFIGPATH="/home/msgc/miraclue/MADA/config/"

LOGPATH="DAClog/"
CONFIG="MADA_config.json"
DAC_null="base_correct_null.dac"

FETCHCON="fetch_config.py"

SETVth_EXE=MADAPATH+"SetVth"
SETDAC_EXE=MADAPATH+"SetDAC"
READMEM_EXE=MADAPATH+"read_CtrlMem"

reset=0

#def parser():
parser=argparse.ArgumentParser()
#    argparser.add_argument("MADA_config_file",type=str,nargs='?',const=None,help='MADA config file')
parser.add_argument("-r",help="reset DACs",action='store_true')
parser.add_argument("-c",help="config file name",default=CONFIG)
args=parser.parse_args()
reset=args.r
CONFIG=args.c
#return(opts)


def p_and_e(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd,shell=True)


#parser = argparse.ArgumentParser()
#parser.add_argument("-c",help="config file name",default=CONFIG)
#args = parser.parse_args( )
#CONFIG=args.c

#print("DAC config file:",DAC_CONFIG)


if(os.path.isdir(LOGPATH)==False):
   cmd="mkdir "+LOGPATH
   subprocess.run(cmd,shell=True)
   
if(os.path.isfile(CONFIG)):
   print(CONFIG," exists.")
else:
   cmd=MADAPATH+FETCHCON
   subprocess.run(cmd,shell=True)
      

with open(CONFIG) as f:
    d = json.load(f)

for i in d['gigaIwaki']:
#    name=d['gigaIwaki'][i]['board name']
    IP=d['gigaIwaki'][i]['IP']
    Vth=d['gigaIwaki'][i]['Vth']
    DACfile=d['gigaIwaki'][i]['DACfile']
    if(reset):
        DACfile=CONFIGPATH+"base_correct_null.dac"
        
    #DAC and Vth writing
    cmd=SETDAC_EXE+" "+IP+" "+DACfile
    p_and_e(cmd)
    #    print(cmd)
    cmd=SETVth_EXE+" "+IP+" "+str(Vth)
    #    print(cmd)
    p_and_e(cmd)
 #   i+=1;


#i=0
#for x in d:
    #memory check and log
    dt=datetime.datetime.now()
    flog=LOGPATH+str(dt.year)+str(dt.month).zfill(2)+str(dt.day).zfill(2)+"-"+str(dt.hour).zfill(2)+str(dt.minute).zfill(2)+str(dt.second).zfill(2)
    with open(flog,'w') as log_out:
        cmd=READMEM_EXE+" "+IP
        subprocess.run(cmd,shell=True,stdout=log_out)       
    print("memory check log:"+flog)    
#    i+=1;

#print("SetAllDAC.py [DAC config json file]")
#print("config file:",CONFIG)
