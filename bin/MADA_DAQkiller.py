#!/usr/bin/env python3

import os
import subprocess
import json
import argparse

import glob
import time
import datetime

CONFIG   = "MADA_config.json"

HOME     = os.environ["HOME"]
RATEPATH = HOME + "/rate/"

MADAIWAKI = "MADA_iwaki"
MADApy    = "MADA.py"
DAQENABLE = "MADA_DAQenable.py"

#read option parameters
def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="config file name", default=CONFIG)
    parser.add_argument("-p", "--period", help="period name", default=-1)
    parser.add_argument("-d", "--direct", help="kill process without pressing the enter key", action="store_true")
    args = parser.parse_args( )

    return args

def main():
    print("### MADAkiller.py start ###")

    args   = parser()
    config = args.config
    per    = args.period

    if per[0] != "p":
        per = "per" + str(per).zfill(4)        
    print("Target directory : " + per)

    #load config file
    with open(config, 'r') as file:
        config_load = json.load(file)

    activeIP=[]
    boardID=[]
    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active']==1:
            activeIP.append(config_load['gigaIwaki'][x]['IP'])
            boardID.append(x)

    if not args.direct:
        s = input('return to kill MADA>')
    endtime = time.time()

    # find the latest info file
    fileID = 0
    file = per + "/*_" + str(fileID).zfill(4) + ".info"
    while len(glob.glob(file)):
        fileID += 1
        file = per + "/*_" + str(fileID).zfill(4) + ".info"
    fileID -= 1  
    file = per + "/*_" + str(fileID).zfill(4) + ".info"  
    print("Target file: " + file)

    size=[]

    for i in range(len(activeIP)):
        
        filename_head = per + "/" + boardID[i] + "_" + str(fileID).zfill(4)
        filename_info = filename_head + ".info"
        filename_mada = filename_head + ".mada"
        cmd = 'ls -l ' + filename_mada
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0].decode('utf-8')
        sizel = str(proc).split()
        
        dmes = {}
        dmes['end'] = endtime
        dmes['size'] = sizel[4]
        
        size.append(sizel[4])
        ddmes = {"runinfo":dmes}
        with open(filename_info, 'r') as file:
            info_load = json.load(file)

        dict_giga={}
        dict_info={}
        for x in info_load['gigaIwaki']:
            dict_giga.update(info_load['gigaIwaki'])
        for x in info_load['runinfo']:
            dict_info.update(info_load['runinfo'])
        starttime = dict_info["start"]
        dict_info.update(dmes)
        
        dict={"gigaIwaki":dict_giga,"runinfo":dict_info}
        
        with open(filename_info, mode='w', encoding='utf-8') as file:
            json.dump(dict, file, ensure_ascii=False, indent=2)        

        y = str(datetime.datetime.fromtimestamp(endtime).year)
        m = str(datetime.datetime.fromtimestamp(endtime).month)
        d = str(datetime.datetime.fromtimestamp(endtime).day)
        hh = str(datetime.datetime.fromtimestamp(endtime).hour)
        mm = str(datetime.datetime.fromtimestamp(endtime).minute)
        ss = str(datetime.datetime.fromtimestamp(endtime).second)
        ofile = RATEPATH + y + m.zfill(2) + d.zfill(2)
        t = y + "/" + m.zfill(2) + "/" + d.zfill(2) + "/" + hh.zfill(2) + ":" + mm.zfill(2) + ":" + ss.zfill(2)

        realtime = endtime - starttime
            
    with open(ofile, 'a') as file:
        file.write(t + "\t" + str(starttime) + "\t" + str(endtime) + "\t" + str(size[0]) + "\t"+str(size[1]) + "\t"+str(float(size[0]) / realtime) + "\t" + str(float(size[1]) / realtime) + "\n")
    
    exes = [MADApy, MADAIWAKI, DAQENABLE]
    for exe in exes:
        cmd = "ps -aux | grep " + exe + " | grep -v 'ps -aux' |awk '{print $2}'"
        print('Execute: ' + cmd)
        pid = subprocess.run(cmd, shell=True, encoding='utf-8', stdout=subprocess.PIPE).stdout.replace("\n", " ")
        print(pid)
        cmd = "kill " + pid
        subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    main()