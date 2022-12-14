#!/usr/bin/python3

import argparse
import datetime
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from subprocess import PIPE

HOME = os.environ["HOME"]

# scripts
MADAPATH = "/home/msgc/miraclue/MADA/bin/"
ADAPATH = "/home/msgc/adalm/adalm_out"
FETCHCON = MADAPATH+"MADA_fetch_config.py"
Enable = MADAPATH+"MADA_DAQenable.py"
TestPulse = MADAPATH+"MADA_testout.py -f 1000"
VthScan = MADAPATH+"MADA_runVthScan.py"
KILLER = MADAPATH+"MADA_killmodules.py"

# configs
CONFIG = "MADA_config.json"
CONFIG_SKEL = "MADA_config_SKEL.json"

LOGPATH = "/home/msgc/miraclue/log/VthCheck/"


def run_commands(cmd_list, max_workers):
    def run(cmd):
        print(f"running: {cmd}")
        subprocess.run(cmd, shell=True)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(run, cmd_list)


PIDs = []
parser = argparse.ArgumentParser()
parser.add_argument("--step", "-s", type=int, default=100)
args = parser.parse_args()

VthStep = args.step
print("Vth Step:", VthStep)

# fetch config file
cmd = FETCHCON
print(cmd)
proc = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
# fetch config file ends

# load config file
config_open = open(CONFIG, 'r')
config_load = json.load(config_open)
activeIP = []
Vth = []
for x in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][x]['active'] == 1:
        Vth.append(config_load['gigaIwaki'][x]['Vth'])
        activeIP.append(config_load['gigaIwaki'][x]['IP'])

procEnable = subprocess.Popen(Enable, stdout=subprocess.PIPE)
procTP = subprocess.Popen(TestPulse, stdout=subprocess.PIPE, shell=True)

active_board_count = len(activeIP)
print("Number of Iwaki boards: ", active_board_count)
vth_scan_comannds = []
for i in range(active_board_count):
    print(activeIP[i], end="\t")
    print(Vth[i])
    print(activeIP[i].split(".", 3))
    if int(activeIP[i].split(".")[3]) < 20:
        Vthlow = Vth[i]-400
        Vthhigh = Vth[i]+1000
    else:
        Vthlow = Vth[i]-1000
        Vthhigh = Vth[i]+400
    cmd = f"{VthScan} -b {activeIP[i]} {Vthlow} {Vthhigh} {VthStep}"
    vth_scan_comannds.append(cmd)

run_commands(vth_scan_comannds, 1)


procEnable.kill()
procTP.kill()

# directory check
p = 0
while (os.path.isdir("Vth_run"+str(p).zfill(4))):
    p += 1


p -= active_board_count

pngs = ""
for i in range(active_board_count):
    png = "Vth_run"+str(p).zfill(4)+"/Vthcheck.png "
    print("written in ", png)
    pngs += png
    p += 1

y = str(datetime.date.today().year)
m = str(datetime.date.today().month)
d = str(datetime.date.today().day)
hh = str(datetime.datetime.now().hour)
mm = str(datetime.datetime.now().minute)
ss = str(datetime.datetime.now().second)
ofile = y+m.zfill(2)+d.zfill(2)+hh.zfill(2)+mm.zfill(2)+ss.zfill(2)+".png"
cmd = "montage "+pngs+" -geometry 800x600 "+ofile
print(cmd)
print("written in", ofile)
pnum = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0].decode('utf-8')
cmd = "cp "+ofile+" LOGPATH"

subprocess.run(KILLER, shell=True)
