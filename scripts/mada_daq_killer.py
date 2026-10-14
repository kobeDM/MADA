#!/usr/bin/env python3

import os
import json
import argparse
import psutil

import glob
import time

from mada_config import load_config, active_boards
from mada_rate_log import write_rate_log

CONFIG   = "MADA_config.json"

HOME     = os.environ["HOME"]
RATEPATH = HOME + "/rate"

target_modules = [
    'MadaIwaki'
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

def update_latest_info(config):
    period = get_latest_period()
    period_name = 'per' + str(period-1).zfill(4)

    boards = active_boards(load_config(config))
    endtime = time.time()

    latest_file_id = get_latest_file_id(period_name)
    if latest_file_id < 0:
        print(f'No info file in {period_name}; nothing to finalize.')
        return

    size_list = []
    starttime = None
    for board_id, board_ip in boards:
        base = period_name + "/" + board_id + "_" + str(latest_file_id).zfill(4)
        info_file_path = base + ".info"
        mada_file_path = base + ".mada"

        if not os.path.exists(info_file_path):
            print(f'WARNING: {info_file_path} not found; skipped.')
            size_list.append(0)
            continue

        size = os.path.getsize(mada_file_path) if os.path.exists(mada_file_path) else 0
        size_list.append(size)

        with open(info_file_path, 'r') as file:
            info_load = json.load(file)

        dict_info = dict(info_load['runinfo'])
        starttime = dict_info["start"]
        dict_info.update({'end': endtime, 'size': size})

        with open(info_file_path, mode='w', encoding='utf-8') as file:
            json.dump({"gigaIwaki": info_load['gigaIwaki'], "runinfo": dict_info},
                      file, ensure_ascii=False, indent=4)

    if starttime is not None:
        write_rate_log(RATEPATH, starttime, endtime, size_list)

def run_daq_killer(config=CONFIG):
    # Always stop the DAQ processes, even if finalizing the info files fails.
    try:
        update_latest_info(config)
    finally:
        run_kill_daq()

def main():
    args   = arg_parser()
    config = args.config
    run_daq_killer(config=config)

if __name__ == "__main__":
    main()