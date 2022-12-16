#!/usr/bin/python3

import argparse
import datetime
import glob
import json
import os
import subprocess
import sys
import time

# configs
CONFIG = "MADA_config.json"

HOME = os.environ["HOME"]
RATEPATH = HOME+"/rate/"


MADAIWAKI = "MADA_iwaki"
MADApy = "MADA.py"

# read option parameters
parser = argparse.ArgumentParser()
parser.add_argument("-c", help="config file name", default=CONFIG)
parser.add_argument("-p", help="pername", default=-1)
args = parser.parse_args()
config = args.c
per = args.p

if per[0] != "p":
    per = "per"+str(per).zfill(4)

print("**MADAkiller.py**")
print(" target dir: "+per)

# load config file
config_open = open(config, 'r')
config_load = json.load(config_open)
activeIP = []
boardID = []
for x in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][x]['active'] == 1:
        activeIP.append(config_load['gigaIwaki'][x]['IP'])
        boardID.append(x)
#        print(config_load['gigaIwaki'][x]['IP'])
# load config file ends.


endtime = time.time()  # .now().timestamp()

# find the latest info file
fileID = 0
file = per+"/*_"+str(fileID).zfill(4)+".info"
while (len(glob.glob(file))):
    fileID = fileID+1
    file = per+"/*_"+str(fileID).zfill(4)+".info"
fileID = fileID-1
file = per+"/*_"+str(fileID).zfill(4)+".info"
print(" target file: "+file)

size = []
for i in range(len(activeIP)):
    filename_head = per+"/"+boardID[i]+"_"+str(fileID).zfill(4)
    filename_info = filename_head+".info"
    filename_mada = filename_head+".mada"
    cmd = 'ls -l '+filename_mada
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            shell=True).communicate()[0].decode('utf-8')
#    print(proc)
    sizel = str(proc).split()
#    print("size= ",str(sizel[4]),"byte")
    dmes = {}
 #   dmes['start']=starttime
    dmes['end'] = endtime
    dmes['size'] = sizel[4]
#    print(str(i)+" ")
    size.append(sizel[4])
    ddmes = {"runinfo": dmes}
    info_open = open(filename_info, 'r')
    info_load = json.load(info_open)
    dict_giga = {}
    dict_info = {}
    for x in info_load['gigaIwaki']:
        dict_giga.update(info_load['gigaIwaki'])
    for x in info_load['runinfo']:
        dict_info.update(info_load['runinfo'])
    starttime = dict_info["start"]
    #    print(starttime)
    dict_info.update(dmes)
    dict = {"gigaIwaki": dict_giga, "runinfo": dict_info}
    with open(filename_info, mode='w', encoding='utf-8') as file:
        json.dump(dict, file, ensure_ascii=False, indent=2)

    y = str(datetime.datetime.fromtimestamp(endtime).year)
    m = str(datetime.datetime.fromtimestamp(endtime).month)
    d = str(datetime.datetime.fromtimestamp(endtime).day)
    hh = str(datetime.datetime.fromtimestamp(endtime).hour)
    mm = str(datetime.datetime.fromtimestamp(endtime).minute)
    ss = str(datetime.datetime.fromtimestamp(endtime).second)
    ofile = RATEPATH+y+m.zfill(2)+d.zfill(2)  # +"_"+str(i)
    t = y+"/"+m.zfill(2)+"/"+d.zfill(2)+"/"+hh.zfill(2)+":"+mm.zfill(2)+":"+ss.zfill(2)

    realtime = endtime-starttime

# FIXME range(4)は明らかにボード4枚を想定している
# やっつけ修理20221214身内
f = open(ofile, 'a')
#rate = []
#for ii in range(4):
#for ii in range(6):
#    rate.append(float(size[ii])/realtime)
#f.write(t+"\t"+str(starttime)+"\t"+str(endtime)+"\t"+str(size[0])+"\t"+str(size[1])+"\t"+str(size[2])+"\t"+str(size[3])+"\t"+str(float(size[0])/realtime)+"\t"+str(float(size[1])/realtime)+"\t"+str(float(size[2])/realtime)+"\t"+str(float(size[3])/realtime)+"\n")
f.write(t+"\t"+str(int(starttime))+"\t"+str(int(endtime))+"\t"+str(int(size[0]))+"\t"+str(int(size[1]))+"\t"+str(int(size[2]))+"\t"+str(int(size[3]))+"\t"+str(int(size[4]))+"\t"+str(int(size[5]))+"\t"+str(int(size[0])/realtime)+"\t"+str(int(size[1])/realtime)+"\t"+str(int(size[2])/realtime)+"\t"+str(int(size[3])/realtime)+"\t"+str(int(size[4])/realtime)+"\t"+str(int(size[5])/realtime)+"\n")
f.close()
