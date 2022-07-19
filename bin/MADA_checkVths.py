#!/usr/bin/python3

import subprocess, os,sys
import argparse
import subprocess
from subprocess import PIPE
import json
import time
import datetime

HOME=os.environ["HOME"]

#scripts
MADAPATH="/home/msgc/miraclue/MADA/bin/"
ADAPATH="/home/msgc/adalm/adalm_out"
FETCHCON=MADAPATH+"MADA_fetch_config.py"
Enable=MADAPATH+"MADA_DAQenable.py"
TestPulse=MADAPATH+"MADA_testout.py -f 1000"
VthScan=MADAPATH+"MADA_runVthScan.py"
KILLER=MADAPATH+"MADA_killmodules.py"

#configs
CONFIG="MADA_config.json"
CONFIG_SKEL="MADA_config_SKEL.json"

LOGPATH="/home/msgc/miraclue/log/VthCheck/"

PIDs=[]
VthStep=100
#print("IP:",IP)
#print("Vth low:",VthLow)
#print("Vth high:",VthHigh)
print("Vth Step:",VthStep)

#fetch config file
cmd=FETCHCON
print(cmd)
proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
#fetch config file ends

#load config file
config_open= open(CONFIG,'r')
config_load = json.load(config_open)
activeIP=[]
Vth=[]
for x in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][x]['active']==1:
        Vth.append(config_load['gigaIwaki'][x]['Vth'])
        activeIP.append(config_load['gigaIwaki'][x]['IP'])
#        print(config_load['gigaIwaki'][x]['IP'])
#load config file ends.

#kill related programs
KILLER=MADAPATH+"MADA_killmodules.py"


#make new directory
#p=0
#while(os.path.isdir("Vthcheck"+str(p).zfill(4))):
#      print("per",p," exixts.")
#      p+=1
      
#newper="Vthcheck"+str(p).zfill(4)
#cmd="mkdir "+newper+"; cd "+newper
#proc=subprocess.run(cmd,shell=True)
#print("New directory ",newper,"is made.")


#proc=subprocess.run(Enable,shell=True)
#PIDs.append(proc.PID)
procEnable = subprocess.Popen(Enable,stdout=subprocess.PIPE)
procTP = subprocess.Popen(TestPulse,stdout=subprocess.PIPE,shell=True)
#PIDs.append(proc.PID)
#procTP=subprocess.run(TestPulse,shell=True)
#PIDs.append(proc.PID)



print("Number of Iwaki boards: ",len(activeIP))
#for IP in activeIP:
for i in range(len(activeIP)):
    print(activeIP[i],end="\t")
    print(Vth[i])
    print(activeIP[i].split(".",3))
    if int(activeIP[i].split(".")[3]) < 20:
        Vthlow=Vth[i]-400
        Vthhigh=Vth[i]+1000
    else: 
        Vthlow=Vth[i]-1000
        Vthhigh=Vth[i]+400
    cmd=VthScan+" -b "+activeIP[i]+" "+str(Vthlow)+" "+str(Vthhigh)+" 100"
    subprocess.run(cmd,shell=True)
#    print(com)
#print(PIDs)


procEnable.kill()
procTP.kill()

#directory check
p=0
while(os.path.isdir("Vth_run"+str(p).zfill(4))):
#      print("per",p," exixts.")
      p+=1
      

p-=4

pngs=""
for i in range(len(activeIP)):
    png="Vth_run"+str(p).zfill(4)+"/Vthcheck.png "
    print("written in ",png)
    pngs+=png
    p+=1
#CMD=EXE_ANA+" -b "+newrun

y  =    str(datetime.date.today().year)
m  =    str(datetime.date.today().month)
d  =    str(datetime.date.today().day)
hh  =    str(datetime.datetime.now().hour)
mm  =    str(datetime.datetime.now().minute)
ss  =    str(datetime.datetime.now().second)
ofile=y+m.zfill(2)+d.zfill(2)+hh.zfill(2)+mm.zfill(2)+ss.zfill(2)+".png"
cmd="montage "+pngs+" -geometry 800x600 "+ofile+"; eog  "+ ofile+"&"
print(cmd)
print("written in",ofile)
#subprocess.run(cmd,shell=True)
pnum = (subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         shell=True).communicate()[0]).decode('utf-8')
cmd="cp "+ofile+" LOGPATH"

subprocess.run(KILLER,shell=True)
