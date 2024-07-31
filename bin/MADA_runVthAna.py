#!/usr/bin/python3
import subprocess, os,sys
import argparse
import glob
from subprocess import PIPE
import json
from csv import reader

#EXEPATH="/home/msgc/miraclue/gigaiwaki_ana/bin"
EXEPATH="/home/msgc/miraclue/gigaiwaki_ana/src"
MADAPATH="/home/msgc/miraclue/MADA/bin/"
EXE="Vth_Analysis"
SKEL="ShowVth_skel.cxx"
SHOW_CODE="ShowVth.cxx"


#configs
CONFIG="MADA_config.json"

def parser():
    argparser=argparse.ArgumentParser()
    argparser.add_argument("runID",type=str,nargs='?',const=None,help='[runID]')
    argparser.add_argument("-b","--batch", help="batch mode",dest='batch',action="store_true")
    opts=argparser.parse_args()
    return(opts)

def p_and_e(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd,shell=True)



args=parser()
if(args.runID):
    run=args.runID
else:
    run="Vth_run0000"

if args.batch:
    #switch for batch mode
    print("batch mode")
    batch_mode=1
else:
    batch_mode=0


print("runID:",run)
configfile=run+'/scan_config.out'
print("config file:",configfile)

#f = open(configfile, 'r')
#config = f.readlines()

with open(configfile, 'r') as csv_file:
    csv_reader = reader(csv_file, delimiter = ' ')
    config = list(csv_reader)
#    print(list_of_rows)
#    print(list_of_rows[0])
#    row0=list_of_rows[0]
#    print(row0[0])
#print(config)
#print(config[0])
#row0=config[0]
#print(row0[0])


#print(config)
l_Vth=[ line for line in config if 'Vth(lower):' in line ]
#print(l_Vth)
VthLow=l_Vth[0][1]


l_Vth=[ line for line in config if 'Vth(upper):' in line ]
print(l_Vth)
VthHigh=l_Vth[0][1]

l_Vth=[ line for line in config if 'Vth(delta):' in line ]
print(l_Vth)
VthStep=l_Vth[0][1]

l_IP=[ line for line in config if 'IP:' in line ]
IP=l_IP[0][1]
#print(IP[1])
#VthStep=l_Vth[0][1]

if os.path.exists(CONFIG):
    #load config file
    config_open= open(CONFIG,'r')
    config_load = json.load(config_open)
    for x in config_load['gigaIwaki']:
        if IP == config_load['gigaIwaki'][x]['IP']:
            Vth=config_load['gigaIwaki'][x]['Vth']
else:
    Vth=0


EXECOM=EXEPATH+"/"+EXE+" "+run+" "+VthLow+" "+VthHigh+" "+VthStep
print("execute:",EXECOM)
subprocess.run(EXECOM,shell=True)

#SKEL_FULL=EXEPATH+'/'+SKEL
SKEL_FULL=MADAPATH+'/'+SKEL

with open(SKEL_FULL, mode='r') as f:
    str_list = f.readlines()
#    print(str_list)
    showcode = [ s.replace("RUNID",run).replace("IP",IP).replace("VTH",str(Vth))  for s in str_list ]
#    showcode = [ s.replace("RUNID",run)  for s in str_list ]
#    print(showcode)


with open(SHOW_CODE, mode='w') as f:
    f.writelines(showcode)

if batch_mode:
    CMD='root -b -q '+SHOW_CODE
else:
    CMD='root '+SHOW_CODE

p_and_e(CMD)



