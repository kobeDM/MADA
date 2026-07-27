#!/usr/bin/env python3

import os
import subprocess
from subprocess import PIPE
import json
import datetime

MADAHOME = os.environ["MADAHOME"]
ADAHOME  = os.environ["ADAHOME"]

MADABIN   = MADAHOME + '/bin'

#scripts
ADAPATH   = "/home/msgc/cn_tc/adalm/adalm_out"
FETCHCON  = MADABIN + "/MADA_fetch_config.py"
Enable    = MADABIN + "/MADA_DAQenable.py"
TestPulse = MADABIN + "/MADA_testout.py -f 1000"
VthScan   = MADABIN + "/MADA_runVthScan.py"
KILLER    = MADABIN + "/MADA_killmodules.py"

#configs
CONFIG = "MADA_config.json"

LOGPATH = "/home/msgc/miraclue/log/VthCheck/"

PIDs = []
VthStep = 100
# print("IP:",IP)
# print("Vth low:",VthLow)
# print("Vth high:",VthHigh)
print("Vth Step:", VthStep)

# fetch config file
cmd = FETCHCON
print(cmd)
proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)

# load config file
# config_open = open(CONFIG,'r')
# config_load = json.load(config_open)
with open(CONFIG, 'r') as config_open:
    config_load = json.load(config_open)

activeIP = []
Vth = []
for x in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][x]['active'] == 1:
        Vth.append(config_load['gigaIwaki'][x]['Vth'])
        activeIP.append(config_load['gigaIwaki'][x]['IP'])

# kill related programs
KILLER = MADABIN + "/MADA_killmodules.py"

procEnable = subprocess.Popen(Enable,stdout=subprocess.PIPE)
procTP     = subprocess.Popen(TestPulse,stdout=subprocess.PIPE,shell=True)

print("Number of Iwaki boards: ", len(activeIP))

for i in range(len(activeIP)):
    print(activeIP[i],end="\t")
    print(Vth[i])
    print(activeIP[i].split(".",3))
    if int(activeIP[i].split(".")[3]) < 20: # anode
        Vthlow  = Vth[i] - 400
        Vthhigh = Vth[i] + 1000
    else: # cathode
        Vthlow  = Vth[i] - 1000
        Vthhigh = Vth[i] + 400
    cmd = VthScan + " -b " + activeIP[i] + " "+str(Vthlow) + " " + str(Vthhigh) + " 100"
    subprocess.run(cmd,shell=True)

procEnable.kill()
procTP.kill()

# directory check
p = 0
while(os.path.isdir("Vth_run"+str(p).zfill(4))):
    p += 1
p -= 4

pngs = ""
for i in range(len(activeIP)):
    png="Vth_run"+str(p).zfill(4)+"/Vthcheck.png "
    print("written in ", png)
    pngs += png
    p += 1

y   =    str(datetime.date.today().year    )
m   =    str(datetime.date.today().month   )
d   =    str(datetime.date.today().day     )
hh  =    str(datetime.datetime.now().hour  )
mm  =    str(datetime.datetime.now().minute)
ss  =    str(datetime.datetime.now().second)
ofile = y + m.zfill(2) + d.zfill(2) + hh.zfill(2) + mm.zfill(2) + ss.zfill(2) + ".png"
cmd = "montage " + pngs + " -geometry 800x600 " + ofile + "; eog  " +  ofile + "&"
print(cmd)
print("written in", ofile)
#subprocess.run(cmd,shell=True)
pnum = (subprocess.Popen(cmd,stdout=subprocess.PIPE,shell=True).communicate()[0]).decode('utf-8')
cmd = "cp "+ofile+" LOGPATH"

subprocess.run(KILLER,shell=True)
