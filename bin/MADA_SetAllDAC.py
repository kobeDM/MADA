#!/usr/bin/python3
import subprocess, os,sys
import argparse
import json
import datetime

from subprocess import PIPE

#scripts
FETCHCON="MADA_fetch_config.py"
findADALM="findADALM2000.py"
SETDAC="MADA_SetAllDACs.py"


#configs
CONFIG="MADA_config.json"
CONFIG_SKEL="MADA_config_SKEL.json"

#DAC_CONFIG_DEFAULT="/home/msgc/miraclue/gigaiwaki_daq/bin/DACparam.json"
#DAC_CONFIG_DEFAULT="/home/msgc/miraclue/uPIC31/20210713/Vth_scan/DACparam.20210716.json"
#DAC_CONFIG_DEFAULT="DACparam.20210716.json"
#DAC_CONFIG_DEFAULT="/home/msgc/MADA/config/DACparam_SKEL.json"
#DAC_CONFIG_DEFAULT="/home/msgc/miraclue/MADA/config/MADA_config_SKEL.json"
#DACPATH="/home/msgc/miraclue/DAQ/bin/"

#DACPATH="/home/msgc/miraclue/gigaiwaki_daq/bin/"
MADAPATH="/home/msgc/miraclue/MADA/bin/"
DACPATH="/home/msgc/miraclue/MADA/bin/"
LOGPATH="/home/msgc/miraclue/log/"
#SETVth_EXE=DACPATH+"SetVth"
#SETDAC_EXE=DACPATH+"SetDAC"
#READMEM_EXE=DACPATH+"read_CtrlMem"
SETVth_EXE=MADAPATH+"SetVth"
SETDAC_EXE=MADAPATH+"SetDAC"
READMEM_EXE=MADAPATH+"read_CtrlMem"

def parser():
    argparser=argparse.ArgumentParser()
    argparser.add_argument("config_file",type=str,nargs='?',const=None,help='config file')
    opts=argparser.parse_args()
    return(opts)


def p_and_e(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd,shell=True)


args=parser()
if(args.config_file):
    CONFIG=args.config_file
#else:
#    CONFIG=CONFIG_DEFAULT


#fetch config file
cmd=MADAPATH+FETCHCON
print(cmd)
proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
#fetch config file ends


    
    
print("DAC config file:",CONFIG)

#with open(CONFIG) as f:
#    d = json.load(f)

#i=0
        
#load config file
config_open= open(CONFIG,'r')
config_load = json.load(config_open)
activeIP=[]
for x in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][x]['active']==1:
        activeIP.append(config_load['gigaIwaki'][x]['IP'])
        #    name=config_load['gigaIwaki'][x]['board name']
        name=x
        IP=config_load['gigaIwaki'][x]['IP']
        Vth=config_load['gigaIwaki'][x]['Vth']
        DACfile=config_load['gigaIwaki'][x]['DACfile']
        #  numIwaki+=1
        print(config_load['gigaIwaki'][x]['IP'])
        #DAC and Vth writing
        cmd=SETDAC_EXE+" "+IP+" "+DACfile
        p_and_e(cmd)
        #    print(cmd)
        cmd=SETVth_EXE+" "+IP+" "+str(Vth)
        #    print(cmd)
        p_and_e(cmd)
        #for x in d:
        #memory check and log
        dt=datetime.datetime.now()
        flog=LOGPATH+str(dt.year)+str(dt.month).zfill(2)+str(dt.day).zfill(2)+"-"+str(dt.hour).zfill(2)+str(dt.minute).zfill(2)+str(dt.second).zfill(2)+"-"+name
        with open(flog,'w') as log_out:
            cmd=READMEM_EXE+" "+IP
            subprocess.run(cmd,shell=True,stdout=log_out)
            print("memory check log:"+flog)    
 #           i+=1;

#print("SetAllDAC.py [config json file]")
#print("config file:",CONFIG)
