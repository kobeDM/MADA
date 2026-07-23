#!/usr/bin/env python3

import os
import json
import argparse
import psutil

import glob
import time
import datetime

CONFIG   = "MADA_config.json"

HOME     = os.environ["HOME"]
RATEPATH = HOME + "/rate"

target_modules = [
    'MADA_DAQenable.py',
    'MADA_iwaki'
]

#read option parameters
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="config file name", default=CONFIG)
    args = parser.parse_args( )
    return args

def get_latest_period():
    period = 0
    while os.path.exists('per' + str(period).zfill(4)):
        period += 1
    return period

def get_latest_file_id(period_name):
    file_id = 0
    file = period_name + "/*_" + str(file_id).zfill(4) + ".info"
    while len(glob.glob(file)):
        file_id += 1
        file = period_name + "/*_" + str(file_id).zfill(4) + ".info"
    return file_id - 1

def get_active_boards(config_path):
    with open(config_path, 'r') as file:
        config_load = json.load(file)

    active_boards = []
    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active'] == 1:
            active_boards.append((x, config_load['gigaIwaki'][x]['IP']))
    return active_boards

def run_kill_daq():
    killed_pids = set()

    for proc in psutil.process_iter(['pid', 'cmdline']):
        cmdline = ' '.join(proc.info['cmdline'] or [])

        if any(module in cmdline for module in target_modules):
            print(f"Killing PID {proc.pid}: {cmdline}")
            proc.terminate()
            killed_pids.add(proc.pid)
        
    if not killed_pids:
        print("No MADA-related processes found to kill.")

    return killed_pids

def run_daq_killer(config=CONFIG):

    period = get_latest_period()
    period_name = 'per' + str(period-1).zfill(4)

    #load config file
    active_boards = get_active_boards(config)

    endtime = time.time()

    # find the latest info file
    latest_file_id  = get_latest_file_id(period_name)

    size_list=[]
    for i in range(len(active_boards)):
        board_id, board_ip = active_boards[i]        
        info_file_path = period_name + "/" + board_id + "_" + str(latest_file_id).zfill(4) + ".info"
        mada_file_path = period_name + "/" + board_id + "_" + str(latest_file_id).zfill(4) + ".mada"
        
        size = os.path.getsize(mada_file_path)
        
        dmes = {}
        dmes['end'] = endtime
        dmes['size'] = size
        
        size_list.append(size)

        # update info file
        with open(info_file_path, 'r') as file:
            info_load = json.load(file)

        dict_giga = {}
        dict_info = {}
        for x in info_load['gigaIwaki']:
            dict_giga.update(info_load['gigaIwaki'])
        for x in info_load['runinfo']:
            dict_info.update(info_load['runinfo'])
        starttime = dict_info["start"]
        dict_info.update(dmes)
        
        dict = {
            "gigaIwaki":dict_giga,
            "runinfo":dict_info
        }
        
        # write rate file
        with open(info_file_path, mode='w', encoding='utf-8') as file:
            json.dump(dict, file, ensure_ascii=False, indent=4)

        dt = datetime.datetime.fromtimestamp(endtime)

        rate_file_path = dt.strftime(f"{RATEPATH}/%Y%m%d")
        t = dt.strftime("%Y/%m/%d/%H:%M:%S")
        
        realtime = endtime - starttime
        rate     = float(size) / realtime
            
        with open(rate_file_path, 'a') as file:
            file.write(f"{t} {starttime} {endtime} {realtime} {rate}\n")

    run_kill_daq()

def main():
    args   = arg_parser()
    config = args.config
    run_daq_killer(config=config)

if __name__ == "__main__":
    main()