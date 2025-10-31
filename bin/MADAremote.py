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
RATEPATH      = HOME     + '/rate/'

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
CONFIG        = 'MADA_config.json'

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', help='config file path',    default=CONFIG     )
    parser.add_argument('-n', help='file size in MB',     default=num        )
    parser.add_argument('-f', help='maximum file number', default=fileperdir )
    parser.add_argument('-r', '--remote', help='Start DAQ in remote', action='store_true')
    args = parser.parse_args()

    return args

print('*********************************************************')
print('*** MADA.py                                           ***')
print('*** Micacle Argon DAQ (http://github.com/kobeDM/MADA) ***')
print('*** Author      : K. Miuchi (2021 Sep)                ***')
print('*********************************************************')

num         = 10   # default data size in Mbyte 
num_max     = 100  # maximum data size (Mbyte)
fileperdir  = 1000 # maximum file number

# read option parameters
args = parser()
config     = args.c
num        = args.n
fileperdir = args.f

if float(num) > num_max:
    print('File size is too large. Applied ' + str(num_max) + ' Mbyte/file.')
    num = num_max

print('data size per file: ' + str(num) + ' Mbyte')
print('---')
    
# load config file
print('Config file: ' + config)

with open(config, 'r') as config_open:
    config_load = json.load(config_open)

activeIP = []
boardID  = []
for id in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][id]['active']:
        activeIP.append(config_load['gigaIwaki'][id]['IP'])
        boardID.append(id)
        print('Board IP: ' + config_load['gigaIwaki'][id]['IP'])
            
print('Total number of activated Iwaki boards: ' + str(len(activeIP)))
print('---')

# make new period
period = 0
while (os.path.isdir('per' + str(period).zfill(4))):
    period += 1
newper = 'per' + str(period).zfill(4)
cmd    = 'mkdir ' + newper
proc   = subprocess.run(cmd, shell=True)
cmd    = 'cp ' + CONFIG + ' ' + newper
proc   = subprocess.run(cmd, shell=True)
print('New directory ' + newper + ' is made.')
print('---')

# kill runnning modules
subprocess.run(MODULEKILLER, shell=True)
print('---')

# Make kill window
if not (args.remote):
    cmd = 'xterm -geometry 50x5+50+850 -title \'MADA killer\' -background black -foreground green -e ' + DAQKILLER + ' -p ' + str(newper)
    prockiller = subprocess.Popen(cmd, shell=True)

# run DAQ
fileID = 0
while fileID < int(fileperdir):
    print('file: ' + str(fileID) + '/' + str(fileperdir))
    print()

    # kill running processes on ADALM
    cmd = ADKILLER
    subprocess.run(cmd, shell=True)
    print()

    # latch down DAQ enable
    cmd = DISABLE
    subprocess.run(cmd, shell=True)
    print()
    
    # DAC reset in case LV was dropped in the last file
    cmd = SETDAC 
    subprocess.run(SETDAC, shell=True)
    print()

    pids = []
    for i in range(len(activeIP)): # run DAQ
        IP = activeIP[i]
        filename_head = newper + '/' + boardID[i] + '_' + str(fileID).zfill(4)
        filename_info = filename_head + '.info'
        filename_mada = filename_head + '.mada'
        
        print('Board ' + IP + ' info was written in ' + filename_info)
        print('IP:', IP)

        if args.remote:
            cmd = MADAIWAKI + ' -n ' + str(num) + ' -f ' + str(filename_mada) + ' -i ' + IP 
        else:
            cmd = 'xterm -geometry 50x10+50+' + str(i*200) + ' -e '+ MADAIWAKI + ' -n ' + str(num) + ' -f ' + str(filename_mada) + ' -i ' + IP 
        
        print('Execute : ' + cmd)
        proc = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=None)
        pids.append(proc.pid)

    # Make window for DAQ enable
    cmd = 'xterm -geometry 50x10+400+0 -e ' + ENABLE
    print('Exectue: ' + cmd)
    proc = subprocess.Popen(cmd,shell=True)
    enablepid = proc.pid

    # Write information
    starttime = time.time()
    for i in range(len(activeIP)):
        IP = activeIP[i]
        filename_head = newper + '/' + boardID[i] + '_'+str(fileID).zfill(4)
        filename_info = filename_head + '.info'
        
        dict = {}
        for id in config_load['gigaIwaki']:
            if (config_load['gigaIwaki'][id]['IP'] == IP):
                dict.update(config_load['gigaIwaki'][id])
                dd            = {'gigaIwaki':dict}
                dmes          = {}
                dmes['start'] = starttime
                ddmes         = {'runinfo':dmes}
                dd.update(ddmes)                
                with open(filename_info, mode='wt', encoding='utf-8') as file:
                    json.dump(dd, file, ensure_ascii=False, indent=2) 
    print()
            
    # Reset trigger count
    subprocess.run(COUNTERRESET, shell=True)
    print()

    print('cmd              :', COUNTERRESET)
    print('GIGAiwaki pids   :', pids)
    print('enable pid       :', enablepid)    
    print('working directory:', newper)
    print('started at        ', starttime)

    running = 1
    while running:
        # Check running DAQ numbers
        runs = 0
        for i in range(len(pids)):
            cmd = 'ps -aux | awk \'$2=='+str(pids[i]) + '\' | wc -l'
            pnum = (subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]).decode('utf-8')
            if int(pnum) == 1:
                runs += 1
 
        # Catch DAQ termination
        if runs < len(pids):
            running = 0
            subprocess.run(ADKILLER, shell=True)
            subprocess.run(DISABLE, shell=True)
            endtime = time.time()

            # kill all running DAQ
            ps       = 'ps -aux | grep -v \' grep \' | grep xterm | grep iwaki'
            process  = (subprocess.Popen(ps, stdout=subprocess.PIPE, shell=True).communicate()[0]).decode('utf-8')
            pl       = process.split('\n')
            killpids = []
            for j in range(len(pl)-1):
                pll = pl[j].split()
                killpids.append(pll[1])
                for i in range(len(killpids)):
                    kill = 'kill -KILL ' + killpids[i]
                    subprocess.run(kill,shell=True)    
            break
            
    # --- Finalize ---
    print('file ' + str(fileID) + 'finished at ' + str(endtime))
    realtime = endtime - starttime
    print('real time = ' + str(realtime))

    # Write log
    size = []
    for i in range(len(activeIP)):
        filename_head = newper + '/' + boardID[i] + '_' + str(fileID).zfill(4)
        filename_info = filename_head + '.info'
        filename_mada = filename_head + '.mada'
        cmd = 'ls -l ' + filename_mada
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,shell=True).communicate()[0].decode('utf-8')
        sizel = str(proc).split()
        print('size= ', str(sizel[4]), 'byte')
        dmes={}
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

    with open(ofile, 'a') as f:
        rate = []
        for ii in range(len(activeIP)):
            rate.append(float(size[ii]) / realtime)
        out_list = [t, starttime, endtime] + size + [float(s) / realtime for s in size]
        out_str = '\t'.join(map(str, out_list)) + '\n'
        f.write(out_str)
    
    fileID += 1
