#!/usr/bin/python3

import os, sys
import subprocess
import numpy
import glob
import time
import argparse
import json

from subprocess import PIPE
from time import sleep
#from subprocess import STDOUT

HOME=os.environ["HOME"]

#PATH
MADAPATH=HOME+"/miraclue/MADA/bin/"
MADACONFIGPATH=HOME+"/miraclue/MADA/config/"

#binary
#MADA="MADA"
#MADACON="MADA_con"
MADAIWAKI="MADA_iwaki"

#scripts
FETCHCON=MADAPATH+"MADA_fetch_config.py"
findADALM=MADAPATH+"findADALM2000.py"
SETDAC=MADAPATH+"MADA_SetAllDACs.py"
ENABLE=MADAPATH+"MADA_DAQenable.py"
DISABLE=MADAPATH+"MADA_DAQenable.py -d"
KILLER=MADAPATH+"MADA_killmodules.py"

#configs
CONFIG="MADA_config.json"
CONFIG_SKEL="MADA_config_SKEL.json"


print("**MADA.py**")
print("**Micacle Argon DAQ (http://github.com/kobeDM/MADA)**")
print("**2021 Sep by K. Miuchi**")

num=100#data size in Mbyte
run_control=0 #option for run control only
#read option parameters
parser = argparse.ArgumentParser()
parser.add_argument("-c",help="config file name",default=CONFIG)
parser.add_argument("-s",help="silent mode (control only)",action='store_true')
parser.add_argument("-n",help="file size in MB",default=num)
args = parser.parse_args( )
CONFIG=args.c
num=args.n
run_control=args.s

#fetch config file
#print(FETCHCON)
proc=subprocess.run(FETCHCON,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
#fetch config file ends

#DAC set
if(run_control==0):
#    print(SETDAC)
    proc=subprocess.run(SETDAC,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
#DAC set

        
#load config file
config_open= open(CONFIG,'r')
config_load = json.load(config_open)
activeIP=[]
boardID=[]
for x in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][x]['active']==1:
        activeIP.append(config_load['gigaIwaki'][x]['IP'])
        boardID.append(x)
        print(config_load['gigaIwaki'][x]['IP'])
#load config file ends.
            
print("Number of Iwaki boards: ",len(activeIP))
#print(activeIP.len)



#make new period
p=0
while(os.path.isdir("per"+str(p).zfill(4))):
#      print("per",p," exixts.")
      p+=1

      
newper="per"+str(p).zfill(4)
cmd="mkdir "+newper
proc=subprocess.run(cmd,shell=True)
cmd="cp "+CONFIG+" "+newper
proc=subprocess.run(cmd,shell=True)
print("New directory ",newper,"is made.")



#cmd="cd "+newper
#proc=subprocess.run(cmd,shell=True)
fileperdir=1000
fileID=0
#DAQ run
#while fileID < fileperdir:
# 
#    print(filename_head)
#    cmd='xterm -e '+MADAPATH+MADAIWAKI +" -i "+IP+" -n "+str(num)+ " -f " + filename_head+" &"
#   proc=subprocess.run(cmd,shell=True)
#print(cmd)

#filename_head=newper+"/GBIP_thisIP"
#filename_head=newper+"/GBKB_thisIP"
#if(run_control):
#    cmd=MADAPATH+MADA+" -s "+" -n "+str(num)+" -f "+str(filename_head)

    #    cmd=MADAPATH+MADACON
#cmd=MADAPATH+MADACON
#proc=subprocess.run(cmd,shell=True)
#+" -n "+str(num)
#else:
#filename_head=newper+"/GBIP_thisIP_"+str(fileID).zfill(4)
#    cmd=MADAPATH+MADA+" -n "+str(num)+" -f "+str(filename_head)
#    print(cmd)
    #proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,Text=True)
    #proc=
#    subprocess.run(cmd,shell=True)


#for IP in activeIP:
#    filename_info=newper+"/GBIP_"+IP.split(".")[3].zfill(3)+"_"+str(fileID).zfill(4)+".info"
#    print("board "+IP+" info was written in "+filename_info)
#    dict={}
#    for x in config_load['gigaIwaki']:
#        if (config_load['gigaIwaki'][x]['IP']==IP):
#            config_load['gigaIwaki'].pop(x)
#            print(x,"\t\t",config_load['gigaIwaki'][x])
#            dict.update(config_load['gigaIwaki'][x])
                    
#    with open(filename_info, mode='wt', encoding='utf-8') as file:
#        json.dump(dict, file, ensure_ascii=False, indent=2)

fileID=0
#DAQ run
while fileID < fileperdir:
    print(fileID,"/",fileperdir)
    #print(DISABLE)
    subprocess.run(KILLER,shell=True)
    subprocess.run(DISABLE,shell=True)
    pids=[]
    for i in range(len(activeIP)):
        IP=activeIP[i]
#        filename_head=newper+"/GBKB_"+IP.split(".")[3].zfill(3)+"_"+str(fileID).zfill(4)
        filename_head=newper+"/"+boardID[i]+"_"+str(fileID).zfill(4)
        filename_info=filename_head+".info"
        filename_mada=filename_head+".mada"
        print("board "+IP+" info was written in "+filename_info)
        dict={}
        for x in config_load['gigaIwaki']:
            if (config_load['gigaIwaki'][x]['IP']==IP):
                dict.update(config_load['gigaIwaki'][x])
                with open(filename_info, mode='wt', encoding='utf-8') as file:
                    json.dump(dict, file, ensure_ascii=False, indent=2)
                    #wirte info file done

                    
        print(IP)
        cmd="xterm -geometry 50x10+100+"+str(i*80)+" -e "+MADAIWAKI+" -n "+str(num)+" -f "+str(filename_mada)+" -i "+IP 
        print(cmd)
        #roc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None)
        proc=subprocess.Popen(cmd,shell=True,stdout=PIPE,stderr=None)
        pids.append(proc.pid)
        
    cmd="xterm -geometry 50x10+100+400 -e "+ENABLE
    #cmd=ENABLE+" &"
    subprocess.Popen(cmd,shell=True)
    print("working directory: ",newper)
    running=1
    ps="ps -aux "
    while running:
        sleep(1)
        runs=0
        for i in range(len(pids)):
            process = (subprocess.Popen(ps, stdout=subprocess.PIPE,
                           shell=True).communicate()[0]).decode('utf-8')
    #        print(process)
            pl=process.split("\n")
#            print(pl)
            for j in range(len(pl)-1):
 #               print((pl[j].split())[1])
                pll=pl[j].split()
#                print(pll[1].replace(" ",""),pids[i])
                if str(pll[1].replace(" ","")) == str(pids[i]):
#                    print("PID ",pids[i]," is running.")
                    runs+=1
                    #            print(pids[0])
                    #        print("running IDs",runs)

        if runs < len(pids):
            running=0
            print("file terminate")
            for i in range(len(pids)):
                kill="kill -KILL "+str(pids[i])
                print(kill)
                subprocess.run(kill,shell=True)
            break
            #            proc.poll()
        
    
            #        print(".",end="")
    print(fileID," finished.")
    fileID+=1
    
