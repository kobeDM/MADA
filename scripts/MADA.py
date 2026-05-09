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
MADABIN       = MADAHOME + '/bin'
RATEPATH      = HOME     + '/rate'

# binary
MADAIWAKI     = 'MADA_iwaki'

# scripts
SETDAC        = MADABIN + '/MADA_SetAllDAC.py'
ENABLE        = MADABIN + '/MADA_DAQenable.py'
DISABLE       = MADABIN + '/MADA_DAQenable.py -d'
COUNTERRESET  = MADABIN + '/MADA_counterreset.py'
DAQKILLER     = MADABIN + '/MADA_DAQkiller.py'
MODULEKILLER  = MADABIN + '/MADA_killmodules.py'
ADKILLER      = MADABIN + '/MADA_killads.py'

#configs
CONFIG        = 'MADA_config.json'

FILE_SIZE_MAX = 128
FILE_NUM_MAX  = 1024

def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config'   , help='config file path'   , default=CONFIG      )
    parser.add_argument('-n', '--file_size', help='file size in MByte' , default=10          )
    parser.add_argument('-f', '--file_num' , help='maximum file number', default=512         )
    parser.add_argument(      '--remote'   , help='Start DAQ in remote', action='store_true' )
    args = parser.parse_args()
    return args

# Search the latest period.
def make_new_period() -> int:
    p = 0
    while os.path.isdir("per"+str(p).zfill(4)):
        p += 1
    newper = "per" + str(p).zfill(4)
    os.makedirs(newper)
    return p

def make_daq_killer_window(period_num):
    cmd = 'xterm -geometry 50x5+50+850 -title \'MADA killer\' -background black -foreground green -e ' + DAQKILLER + ' -p ' + str(period_num)
    prc = subprocess.Popen(cmd, shell=True)
    return prc

def run_daq_killer(period_num):
    cmd = DAQKILLER + ' -p ' + str(period_num) + ' -d'
    prc = subprocess.Popen(cmd, shell=True)
    return prc

def run_kill_modules():
    prc = subprocess.run(MODULEKILLER, shell=True)
    return prc

def run_adalm_killer():
    prc = subprocess.run(ADKILLER, shell=True)
    return prc

def run_daq_enable(latchup=False, in_process=False):
    if latchup:
        cmd = ENABLE
    else:
        cmd = ENABLE + ' -d'

    if in_process:
        prc = subprocess.Popen(cmd, shell=True)
    else:
        prc = subprocess.run(cmd, shell=True)
    return prc

def run_set_dac():
    prc = subprocess.run(SETDAC, shell=True)
    return prc

def run_gigaiwaki(file_size, filename_mada, IP, window_col, is_remote=False):
    if is_remote:
        cmd = MADAIWAKI + ' -n ' + str(file_size) + ' -f ' + str(filename_mada) + ' -i ' + IP
    else:
        cmd = f"xterm -geometry 50x10+50+{window_col} -e {MADAIWAKI} -n {file_size} -f {filename_mada} -i {IP}"
    prc = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=None)
    return prc

def run_counter_reset():
    prc = subprocess.run(COUNTERRESET, shell=True)
    return prc

def run_kill_command(pid):
    print('Kill process with PID:', pid)
    cmd = 'kill -KILL ' + str(pid)
    prc = subprocess.run(cmd, shell=True)
    return prc

def run_daq(file_size, file_num, period_num, config_load, is_remote=False):
    if float(file_size) > FILE_SIZE_MAX:
        print('File size is too large. Applied ' + str(FILE_SIZE_MAX) + ' Mbyte/file.')
        file_size = FILE_SIZE_MAX

    if int(file_num) > FILE_NUM_MAX:
        print('File number is too large. Applied ' + str(FILE_NUM_MAX) + ' files.')
        file_num = FILE_NUM_MAX

    print('Data size per file        : ' + str(file_size) + ' Mbyte')
    print('Number of files per period: ' + str(file_num) + ' files')
        
    # Get board infomation
    activeIP = []
    boardID  = []
    for id in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][id]['active']:
            activeIP.append(config_load['gigaIwaki'][id]['IP'])
            boardID.append(id)
            print('Board ID: ' + id)
            print('Board IP: ' + config_load['gigaIwaki'][id]['IP'])
            print('---')
                
    print('Total number of activated Iwaki boards: ' + str(len(activeIP)))

    if not is_remote:
        print('Start DAQ killer terminal')
        make_daq_killer_window(period_num)

    # kill runnning modules
    print('Kill running modules')
    run_kill_modules()

    # run DAQ
    fileID = 0
    print('--- Start DAQ ---')
    for fileID in range(int(file_num)):
        print('#############################')
        print('File ID: ' + str(fileID) + '/' + str(file_num))
        print('#############################')
        print()

        # kill running processes on ADALM
        print('Kill running processes for ADALM')
        run_adalm_killer()
        print()

        # latch down DAQ enable
        print('Latch down DAQ enable')
        run_daq_enable(latchup=False)
        print()
        
        # DAC value reset (for latch up)
        print('Reset DAC values')
        run_set_dac()
        print()

        pids = []
        print('Start GIGAiwaki')
        for i in range(len(activeIP)):
            ip = activeIP[i]
            filename_head = 'per' + str(period_num).zfill(4) + '/' + boardID[i] + '_' + str(fileID).zfill(4)
            filename_info = filename_head + '.info'
            filename_mada = filename_head + '.mada'
            
            print('Board ' + ip + ' info was written in ' + filename_info)
            print('IP:', ip)

            window_col = i * 500
            prc = run_gigaiwaki(file_size, filename_mada, ip, window_col, is_remote)
            pids.append(prc.pid)

        run_daq_enable(latchup=True, in_process=True)

        start_time = time.time()
        for i in range(len(activeIP)):
            ip = activeIP[i]
            filename_head = 'per' + str(period_num).zfill(4) + '/' + boardID[i] + '_'+str(fileID).zfill(4)
            filename_info = filename_head + '.info'
            
            dict = {}
            for id in config_load['gigaIwaki']:
                if (config_load['gigaIwaki'][id]['IP'] == ip):
                    dict.update(config_load['gigaIwaki'][id])
                    dd            = {'gigaIwaki':dict}
                    dmes          = {}
                    dmes['start'] = start_time
                    ddmes         = {'runinfo':dmes}
                    dd.update(ddmes)                
                    with open(filename_info, mode='wt', encoding='utf-8') as file:
                        json.dump(dd, file, ensure_ascii=False, indent=2) 
        print()
        
        print('Reset counters')
        run_counter_reset()
        print()

        print('GIGAiwaki pids   :', pids)
        print('working directory:', period_num)
        print('started at       :', start_time)

        # Kill the current data taking when any board is filled.
        while True:
            # count the number of running processes for GIGAiwaki
            runs = 0
            for i in range(len(pids)):
                cmd = 'ps -aux | awk \'$2=='+str(pids[i]) + '\' | wc -l'
                pnum = (subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]).decode('utf-8')
                if int(pnum) == 1:
                    runs += 1

            # If any process is not running, kill all processes and break the loop.
            if runs < len(pids):
                run_adalm_killer()
                run_daq_enable(latchup=False)
                end_time = time.time()

                for pid in pids:
                    run_kill_command(pid)
                break
            time.sleep(1)
                
        print('File ' + str(fileID) + ' finished at ' + str(end_time))
        realtime = end_time - start_time
        print('Realtime: ' + str(realtime) + ' sec')

        # write log
        size = []
        for i in range(len(activeIP)):
            filename_head = 'per' + str(period_num).zfill(4) + '/' + boardID[i] + '_' + str(fileID).zfill(4)
            filename_info = filename_head + '.info'
            filename_mada = filename_head + '.mada'
            cmd = 'ls -l ' + filename_mada
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,shell=True).communicate()[0].decode('utf-8')
            sizel = str(proc).split()
            print('size= ', str(sizel[4]), 'byte')
            dmes={}
            dmes['end']   = end_time
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
                
        y     = str(datetime.datetime.fromtimestamp(end_time).year)
        m     = str(datetime.datetime.fromtimestamp(end_time).month)
        d     = str(datetime.datetime.fromtimestamp(end_time).day)
        hh    = str(datetime.datetime.fromtimestamp(end_time).hour)
        mm    = str(datetime.datetime.fromtimestamp(end_time).minute)
        ss    = str(datetime.datetime.fromtimestamp(end_time).second)
        
        if not os.path.isdir(RATEPATH):
            print('Create directory: ' + RATEPATH)
            os.makedirs(RATEPATH)

        rate_file_path = RATEPATH + '/' + y + m.zfill(2) + d.zfill(2)
        t     = y + '/' + m.zfill(2) + '/' + d.zfill(2) + '/' + hh.zfill(2) + ':'+mm.zfill(2) + ':' + ss.zfill(2)

        with open(rate_file_path, 'a') as f:
            rate = []
            for ii in range(len(activeIP)):
                rate.append(float(size[ii])/realtime)
            out_list = [t, start_time, end_time] + size + [float(s) / realtime for s in size]
            out_str = '\t'.join(map(str, out_list)) + '\n'
            f.write(out_str)
        
        fileID += 1

    # close current kill terminal
    if not is_remote:
        ps       = 'ps -aux | grep MADA_DAQkiller'
        process  = (subprocess.Popen(ps, stdout=subprocess.PIPE, shell=True).communicate()[0]).decode('utf-8')
        pl       = process.split('\n')
        killpids = []
        for j in range(len(pl)-1):
            pll = pl[j].split()
            killpids.append(pll[1])
            for i in range(len(killpids)):
                kill = 'kill -KILL ' + killpids[i]
                subprocess.run(kill,shell=True)   


def main():
    print('*********************************************************')
    print('*** MADA.py                                           ***')
    print('*** Micacle Argon DAQ (http://github.com/kobeDM/MADA) ***')
    print('*** Author      : R.Namai (2026 Apl.)                 ***')
    print('*********************************************************')

    # read option parameters
    args   = parser()
    config_path = args.config
    file_size   = args.file_size
    file_num    = args.file_num
    is_remote   = args.remote

    print('Config file: ' + config_path)
    with open(config_path, 'r') as config_open:
        config_load = json.load(config_open)

    while True:
        new_period = make_new_period()
        run_daq(file_size, file_num, new_period, config_load, is_remote)

if __name__ == "__main__":
    main()