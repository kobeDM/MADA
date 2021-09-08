#!/usr/bin/python3

import os, sys
import subprocess
import numpy
import glob
import time
import argparse
import json

from subprocess import PIPE
#from subprocess import STDOUT

MADAPATH="/home/msgc/miraclue/MADA/bin/"
MADA="MADA"
MADACON="MADA_con"
MADAIWAKI="MADA_iwaki"
findADALM="findADALM2000.py"
CONFIG="MADA_config.json"
CONFIG_SKEL="MADA_config_SKEL.json"

print("**MADA.py**")
print("**Micacle Argon DAQ (http://github.com/kobeDM/MADA)**")
print("**2021 Sep by K. Miuchi**")

num=1000
run_control=0 #option for run control only
#read option parameters
parser = argparse.ArgumentParser()
parser.add_argument("-c",help="config file name",default=CONFIG)
parser.add_argument("-n",help="number of events per file",default=num)
args = parser.parse_args( )
CONFIG=args.c
num=args.n

#print("configure file: "+CONFIG)

if(os.path.isfile(CONFIG)):
    print(CONFIG+" exists.")
else:
    # make config file from skelton file
    CONFIG_SKEL=MADAPATH+CONFIG_SKEL
    print("\tMADA config slkelton file: "+CONFIG_SKEL)
    skel_open= open(CONFIG_SKEL,'r')
    skel_load = json.load(skel_open)

    #set ADALM URIs by checking S/Ns
    for x in skel_load['ADALM']:
        SN=skel_load['ADALM'][x]['S/N']
        cmd=MADAPATH+findADALM+" "+SN
        proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
        URI=proc.stdout.decode("utf8").replace("\n","")
        print("\tURI in "+CONFIG_SKEL+" "+skel_load['ADALM'][x]['URI']+" for S/N: "+SN)
        skel_load['ADALM'][x]['URI']=URI
        print("\tnew URI in "+CONFIG+" "+skel_load['ADALM'][x]['URI']+" for S/N: "+SN)    
    
        with open(CONFIG, mode='wt', encoding='utf-8') as file:
            json.dump(skel_load, file, ensure_ascii=False, indent=2)

#prepare config file ends.


#load config file
config_open= open(CONFIG,'r')
config_load = json.load(config_open)
#numIwaki=0
activeIP=[]
for x in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][x]['active']==1:
        activeIP.append(config_load['gigaIwaki'][x]['IP'])
      #  numIwaki+=1
#        print(config_load['gigaIwaki'][x]['IP'])
#load config file ends.
            
print("Number of Iwaki bords: ",len(activeIP))
#print(activeIP.len)

#make new period
p=0
while(os.path.isdir("per"+str(p).zfill(4))):
#      print("per",p," exixts.")
      p+=1

      
newper="per"+str(p).zfill(4)
cmd="mkdir "+newper
proc=subprocess.run(cmd,shell=True)
print("New directory ",newper,"is made.")

#cmd="cd "+newper
#proc=subprocess.run(cmd,shell=True)
#fileperdir=1000
fileID=0
#DAQ run
#while fileID < fileperdir:
# 
#    print(filename_head)
#    cmd='xterm -e '+MADAPATH+MADAIWAKI +" -i "+IP+" -n "+str(num)+ " -f " + filename_head+" &"
#   proc=subprocess.run(cmd,shell=True)
#print(cmd)
#if(run_control):
#    cmd=MADAPATH+MADACON
#cmd=MADAPATH+MADACON
#proc=subprocess.run(cmd,shell=True)
#+" -n "+str(num)
#else:
#filename_head=newper+"/GBIP_thisIP_"+str(fileID).zfill(4)
filename_head=newper+"/GBIP_thisIP"
cmd=MADAPATH+MADA+" -n "+str(num)+" -f "+str(filename_head)
print(cmd)
    #proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,Text=True)
    #proc=
subprocess.run(cmd,shell=True)


for IP in activeIP:
    filename_info=newper+"/GBIP_"+IP.split(".")[3].zfill(3)+"_"+str(fileID).zfill(4)+".info"
    print("board "+IP+" was info written in "+filename_info)
    dict={}
    for x in config_load['gigaIwaki']:
        if (config_load['gigaIwaki'][x]['IP']==IP):
#            config_load['gigaIwaki'].pop(x)
#            print(x,"\t\t",config_load['gigaIwaki'][x])
            dict.update(config_load['gigaIwaki'][x])
            

        
    with open(filename_info, mode='wt', encoding='utf-8') as file:
        json.dump(dict, file, ensure_ascii=False, indent=2)


#    fileID+=1
    
