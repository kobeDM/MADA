#!/usr/bin/env python3

import os
import subprocess
import time
import datetime
import argparse
import json
from subprocess import PIPE

# import MADA_utils
HOME = os.environ['HOME']
MADAHOME = os.environ['MADAHOME']

# PATH
MADABIN       = MADAHOME + '/bin/'
RATEPATH      = HOME + '/rate/'

# binary
MADAIWAKI     = 'MADA_iwaki'

# scripts
SETDAC        = MADABIN + 'MADA_SetAllDAC.py'
ENABLE        = MADABIN + 'MADA_DAQenable.py'
DISABLE       = MADABIN + 'MADA_DAQenable.py -d'
COUNTERRESET  = MADABIN + 'MADA_counterreset.py'
DAQKILLER     = MADABIN + 'MADA_DAQkiller.py'
MODULEKILLER  = MADABIN + 'MADA_killmodules.py'
ADKILLER      = MADABIN + 'MADA_killads.py'

#configs
CONFIG      = 'MADA_config.json'
# CONFIG_SKEL = 'MADA_config_SKEL.json'

# sql_dbname = 'rate'

print('*********************************************************')
print('*** MADA.py                                           ***')
print('*** Micacle Argon DAQ (http://github.com/kobeDM/MADA) ***')
print('*** Author      : K. Miuchi (2021 Sep)                ***')
print('*** Last update : R. Namai  (2024 Jul)                ***')
print('*********************************************************')

num         = 10   # data size in Mbyte 
num_max     = 100  # max size
fileperdir  = 1000

# read option parameters
parser = argparse.ArgumentParser()
parser.add_argument('-c', help='config file path',    default=CONFIG     )
parser.add_argument('-n', help='file size in MB',     default=num        )
parser.add_argument('-f', help='maximum file number', default=fileperdir )
args = parser.parse_args()
CONFIG     = args.c
num        = args.n
fileperdir = args.f

if int(num) > num_max:
    print('File size is too large. Apllied', num_max, 'Mbyte automatically.')
    num = num_max

print('data size per file: '+str(num)+' Mbyte')
print()

# Fetch config file
# cmd = FETCHCON
# print('execute:', cmd)
# ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False, text=True)
# print(ret.stdout)

# Set DAC file
cmd = SETDAC
print('execute:', cmd)
ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False, text=True).stdout
print(ret)
    
# load config file
activeIP = []
boardID  = []
with open(CONFIG, 'r') as config_open:
    config_load = json.load(config_open)
for x in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][x]['active'] == 1:
        activeIP.append(config_load['gigaIwaki'][x]['IP'])
        boardID.append(x)
        print('Board IP:', config_load['gigaIwaki'][x]['IP'])
            
print('Number of Iwaki boards: ', len(activeIP))
print()

# make new period
p = 0
while (os.path.isdir('per' + str(p).zfill(4))):
    p += 1
newper = 'per' + str(p).zfill(4)
cmd    = 'mkdir ' + newper
proc   = subprocess.run(cmd, shell=True)
cmd    = 'cp ' + CONFIG + ' ' + newper
proc   = subprocess.run(cmd, shell=True)
print('New directory', newper, 'is made.')
print()

# fileperdir = 1000
fileID     = 0

# kill modules
subprocess.run(MODULEKILLER, shell=True)
print()

# make kill terminal
cmd        = 'xterm -geometry 50x5+50+850 -title \'MADA killer\' -background black -foreground green -e ' + DAQKILLER + ' -p ' + str(newper)
prockiller = subprocess.Popen(cmd, shell=True)

# print("file per dir: "+str(fileperdir))
# run DAQ
while fileID < int(fileperdir):
    print(fileID, '/', fileperdir)
    print()

    # kill running processes on ADALM
    cmd = ADKILLER
    subprocess.run(cmd, shell=True)
    # latch down DAQ enable
    cmd = DISABLE
    subprocess.run(cmd, shell=True)
    #DAC reset in case LV was dropped in the last file
    cmd = SETDAC 
    subprocess.run(SETDAC, shell=True)

    pids = []
    for i in range(len(activeIP)):
        IP = activeIP[i]
        filename_head = newper + '/'+boardID[i] + '_' + str(fileID).zfill(4)
        filename_info = filename_head + '.info'
        filename_mada = filename_head + '.mada'
        print('board ' + IP + ' info was written in ' + filename_info)
        print('IP:', IP)
        cmd = 'xterm -geometry 50x10+50+'+str(i*200)+' -e '+MADAIWAKI+' -n '+str(num)+' -f '+str(filename_mada)+' -i '+IP 
        print('cmd:', cmd)
        proc = subprocess.Popen(cmd,shell=True,stdout=PIPE,stderr=None)
        pids.append(proc.pid)
        
    cmd = 'xterm -geometry 50x10+400+0 -e ' + ENABLE
    print('to do cmd:', cmd)
    proc = subprocess.Popen(cmd,shell=True)

    starttime = time.time()
    for i in range(len(activeIP)):
        IP = activeIP[i]
        filename_head = newper + '/' + boardID[i] + '_'+str(fileID).zfill(4)
        filename_info = filename_head + '.info'
        dict = {}
        for x in config_load['gigaIwaki']:
            if (config_load['gigaIwaki'][x]['IP']==IP):
                dict.update(config_load['gigaIwaki'][x])
                dd            = {'gigaIwaki':dict}
                dmes          = {}
                dmes['start'] = starttime
                ddmes         = {'runinfo':dmes}
                dd.update(ddmes)                
                with open(filename_info, mode='wt', encoding='utf-8') as file:
                    json.dump(dd, file, ensure_ascii=False, indent=2) 
            
    enablepid = proc.pid
    subprocess.run(COUNTERRESET,shell=True)
    print('cmd              :', COUNTERRESET)
    print('GIGAiwaki pids   :', pids)
    print('enable pid       :', enablepid)    
    print('working directory:', newper)
    print('started at        ', starttime)

    running = 1
    while running:
        runs = 0
        for i in range(len(pids)):
            cmd = 'ps -aux | awk \'$2=='+str(pids[i]) + '\' | wc -l'
            pnum = (subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]).decode('utf-8')
            if int(pnum) == 1:
                runs += 1
 
        # print('running IDs',runs)
        if runs < len(pids):
            running = 0
            print('file terminate')
            subprocess.run(ADKILLER,shell=True)
            subprocess.run(DISABLE,shell=True)
            endtime = time.time()

            ps       = 'ps -aux | grep -v \' grep \' | grep xterm | grep iwaki'
            process  = (subprocess.Popen(ps, stdout=subprocess.PIPE,shell=True).communicate()[0]).decode('utf-8')
            pl       = process.split('\n')
            killpids = []
            for j in range(len(pl)-1):
                pll = pl[j].split()
                killpids.append(pll[1])
                for i in range(len(killpids)):
                    kill='kill -KILL '+killpids[i]
                    subprocess.run(kill,shell=True)    
            break
            
    print('file ', fileID, 'finished at ', str(endtime))
    realtime = endtime - starttime
    print('real time = ', str(realtime))
    size = []
    for i in range(len(activeIP)):
        filename_head = newper + '/' + boardID[i] + '_' + str(fileID).zfill(4)
        filename_info = filename_head + '.info'
        filename_mada = filename_head + '.mada'
        cmd = 'ls -l ' + filename_mada
        # proc=subprocess.run(cmd,shell=True)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,shell=True).communicate()[0].decode('utf-8')
        sizel = str(proc).split()
        print('size= ', str(sizel[4]), 'byte')
        dmes={}
        # dmes['start'] = starttime
        dmes['end']   = endtime
        dmes['size']  = sizel[4]
        size.append(sizel[4])
        ddmes = {'runinfo':dmes}
        info_open = open(filename_info,'r')
        info_load = json.load(info_open)
        dict_giga = {}
        dict_info = {}
        for x in info_load['gigaIwaki']:
            dict_giga.update(info_load['gigaIwaki'])
        for x in info_load['runinfo']:
            dict_info.update(info_load['runinfo'])
        dict_info.update(dmes)
        dict={'gigaIwaki':dict_giga,'runinfo':dict_info}
        with open(filename_info, mode='w', encoding='utf-8') as file:
            json.dump(dict, file, ensure_ascii=False, indent=2)
            
    y     = str(datetime.datetime.fromtimestamp(endtime).year)
    m     = str(datetime.datetime.fromtimestamp(endtime).month)
    d     = str(datetime.datetime.fromtimestamp(endtime).day)
    hh    = str(datetime.datetime.fromtimestamp(endtime).hour)
    mm    = str(datetime.datetime.fromtimestamp(endtime).minute)
    ss    = str(datetime.datetime.fromtimestamp(endtime).second)
    ofile = RATEPATH + y + m.zfill(2) + d.zfill(2)
    t     = y + '/' + m.zfill(2) + '/' + d.zfill(2) + '/' + hh.zfill(2) + ':'+mm.zfill(2) + ':' + ss.zfill(2)

    # write out event rate into DB and tsb
    # starttime, endtime, mada size, , , mada size / realtime, , ,
    with open(ofile, 'a') as f:
        rate = []
        for ii in range(len(activeIP)):
            rate.append(float(size[ii])/realtime)
        out_list = [t, starttime, endtime] + size + [float(s) / realtime for s in size]
        out_str = '\t'.join(map(str, out_list)) + '\n'
        f.write(out_str)
    
    # PENDING: how many boards
    # cursor.execute('insert into MADA_rate(start,end,ch0_size,ch1_size,ch2_size,ch3_size,ch0_rate,ch1_rate,ch2_rate,ch3_rate) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',(str(starttime),str(endtime),str(size[0]),str(size[1]),str(size[2]),str(size[3]),str(rate[0]),str(rate[1]),str(rate[2]),str(rate[3])))
    fileID += 1
