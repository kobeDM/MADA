#!/usr/bin/python3
import subprocess, os,sys
import argparse
import json
import datetime

DAC_CONFIG_DEFAULT="/home/msgc/miraclue/gigaiwaki_daq/bin/DACparam.json"
#DAC_CONFIG_DEFAULT="/home/msgc/miraclue/uPIC31/20210713/Vth_scan/DACparam.20210716.json"
#DAC_CONFIG_DEFAULT="DACparam.20210716.json"
#DACPATH="/home/msgc/miraclue/DAQ/bin/"
DACPATH="/home/msgc/miraclue/gigaiwaki_daq/bin/"
LOGPATH="/home/msgc/miraclue/log/"
SETVth_EXE=DACPATH+"SetVth"
SETDAC_EXE=DACPATH+"SetDAC"
READMEM_EXE=DACPATH+"read_CtrlMem"

def parser():
    argparser=argparse.ArgumentParser()
    argparser.add_argument("DAC_config_file",type=str,nargs='?',const=None,help='DAC config file')
    opts=argparser.parse_args()
    return(opts)


def p_and_e(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd,shell=True)


args=parser()
if(args.DAC_config_file):
    DAC_CONFIG=args.DAC_config_file
else:
    DAC_CONFIG=DAC_CONFIG_DEFAULT

#print("DAC config file:",DAC_CONFIG)

with open(DAC_CONFIG) as f:
    d = json.load(f)

i=0
for x in d:
    name=d[i]['board name']
    IP=d[i]['IP']
    Vth=d[i]['Vth']
    DACfile=d[i]['DACfile']
    
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
    flog=LOGPATH+str(dt.year)+str(dt.month).zfill(2)+str(dt.day).zfill(2)+"-"+str(dt.hour).zfill(2)+str(dt.minute).zfill(2)+str(dt.second).zfill(2)+"-"+name
    with open(flog,'w') as log_out:
        cmd=READMEM_EXE+" "+IP
        subprocess.run(cmd,shell=True,stdout=log_out)
        
    print("memory check log:"+flog)    
    i+=1;

print("SetAllDAC.py [DAC config json file]")
print("DAC config file:",DAC_CONFIG)
