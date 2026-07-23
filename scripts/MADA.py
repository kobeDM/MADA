#!/usr/bin/env python3

import os
import argparse
import subprocess
import json
import time
from datetime import datetime

from MADA_killmodules import run_kill_modules
from MADA_killadalms import run_kill_adalms
from MADA_adalm_control import run_adalm_control, get_adalm_serial
from MADA_SetAllDAC import run_set_all_dac
from MADA_DAQkiller import run_daq_killer
from MADA_SetLatchUpDetect import run_set_latch_up_detect
from MADA_SetAP import run_set_ap

HOME     = os.environ["HOME"]
RATEPATH = HOME + "/rate"

MADAHOME = os.environ['MADAHOME']
MADA_IWAKI = MADAHOME + "/bin/MADA_iwaki"

def print_header():
    print('*********************************************************')
    print('*** MADA.py                                           ***')
    print('*** Micacle Argon DAQ (http://github.com/kobeDM/MADA) ***')
    print('*** Author      : R.Namai (2026 Apl.)                 ***')
    print('*********************************************************')

def arg_parser():
    parser = argparse.ArgumentParser(description='Micacle Argon DAQ (MADA)')
    parser.add_argument('-c', '--config', help='config file name', default='MADA_config.json')
    parser.add_argument('-f', '--file_num', help='File number in a period', default=512, type=int)
    parser.add_argument('-n', '--event_num', help='Event number in a file', default=1000, type=int)
    parser.add_argument('--calin', nargs=2, type=str, help='Calibration input: [IP] [channel (0-127)]', default=None)
    args = parser.parse_args()
    return args

def load_config(config_path):
    with open(config_path, 'r') as f:
        config_load = json.load(f)
    return config_load

def create_new_period() -> int:
    period = 0
    while os.path.exists('per' + str(period).zfill(4)):
        period += 1
    os.makedirs('per' + str(period).zfill(4))
    return period

def get_active_boards(config_path):
    with open(config_path, 'r') as file:
        config_load = json.load(file)

    active_boards = []
    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active'] == 1:
            active_boards.append((x, config_load['gigaIwaki'][x]['IP']))
    return active_boards

def make_info_file(config_path, period_id, file_id, active_boards):
    start_time = time.time()

    with open(config_path, 'r') as file:
        config_load = json.load(file)

    for board_id, ip in active_boards:
        info_file_name = f'per{str(period_id).zfill(4)}/{board_id}_{str(file_id).zfill(4)}.info'
        config_dict = {}

        for gid in config_load['gigaIwaki']:
            if config_load['gigaIwaki'][gid]['IP'] == ip:
                config_dict.update(config_load['gigaIwaki'][gid])

                output_data = {
                    'gigaIwaki': config_dict,
                    'runinfo': {
                        'start': start_time
                    }
                }

                with open(info_file_name, mode='wt', encoding='utf-8') as out_file:
                    json.dump(output_data, out_file, ensure_ascii=False, indent=4)

                break


def run_gigaiwaki(period_id, file_id, event_num, active_boards):
    for board_id, ip in active_boards:
        mada_file_name = f'per{str(period_id).zfill(4)}/{board_id}_{str(file_id).zfill(4)}.mada'
        cmd = f'{MADA_IWAKI} -n {event_num} -f {mada_file_name} -i {ip}'
        subprocess.Popen(cmd, shell=True)


def get_gigaiwaki_processes():
    result = subprocess.run(['pgrep', '-f', 'MADA_iwaki'], stdout=subprocess.PIPE, text=True)
    pids = result.stdout.strip().split('\n')
    return [int(pid) for pid in pids if pid.isdigit()]


def is_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def check_process_termination(pids):
    print('Waiting for gigaiwaki processes to finish...')
    process_num_org = len(pids)

    while True:
        alive_pids = [p for p in pids if is_alive(p)]
        if len(alive_pids) != process_num_org:
            break
        time.sleep(1)


def kill_gigaiwaki_processes(pids):
    for pid in pids:
        try:
            os.kill(pid, 9)
            print(f'Killed process with PID: {pid}')
        except ProcessLookupError:
            print(f'Process with PID {pid} not found. It may have already terminated.')

def update_info_file(period_id, file_id, end_time, active_boards):
    for board_id, ip in active_boards:
        info_file_path = f'per{str(period_id).zfill(4)}/{board_id}_{str(file_id).zfill(4)}.info'
        mada_file_path = f'per{str(period_id).zfill(4)}/{board_id}_{str(file_id).zfill(4)}.mada'

        file_size = os.path.getsize(mada_file_path)
        print('size= ', file_size, 'byte')

        with open(info_file_path, 'r', encoding='utf-8') as f:
            info_load = json.load(f)

        info_load.setdefault('runinfo', {})
        info_load['runinfo'].update({
            'end': end_time,
            'size': str(file_size)
        })

        with open(info_file_path, 'w', encoding='utf-8') as f:
            json.dump(info_load, f, ensure_ascii=False, indent=4)

    return file_size
    
def write_rate_log(rate_file_path, end_time, start_time, event_num):
    realtime = end_time - start_time
    dt = datetime.fromtimestamp(end_time)

    t = dt.strftime("%Y/%m/%d/%H:%M:%S")

    rates = [float(event_num) / realtime]
    out_list = [t, start_time, end_time] + rates
    out_str = '\t'.join(map(str, out_list)) + '\n'

    with open(rate_file_path, 'a', encoding='utf-8') as f:
        f.write(out_str)

def run_daq(config_path, period_id, file_num, event_num, calin=None):
    active_boards = get_active_boards(config_path)
    if calin:
        active_boards = [(board_id, ip) for board_id, ip in active_boards if ip == calin[0]]
    else:
        for board_id, ip in active_boards:
            print(f'Starting DAQ for board {board_id} at IP {ip}')

    run_kill_modules()
    config_load = load_config(config_path)
    adalm_serial_daq_enable = get_adalm_serial(config_load, adalm_index=0)
    adalm_serial_counter_reset = get_adalm_serial(config_load, adalm_index=1)

    print('Activating Regulator...')
    run_set_ap(config_path, io=1)

    print('Setting DAC values and Vth...')
    # run_set_all_dac(config_path, calin)
    run_set_all_dac(config_path)

    print('Activating Latch Up Detection...')
    run_set_latch_up_detect(config_path, io=1)

    print('DAQ is running... Press Ctrl+C to stop.')
    for file_id in range(file_num):
        try:
            print(f'Creating file {file_id} with {event_num} events...')

            print('Killing ADALM processes...')
            run_kill_adalms()

            print('Latch down DAQ enable...')
            run_adalm_control(adalm_serial_daq_enable, latch=0)
            
            print('Running gigaiwaki...')
            run_gigaiwaki(period_id, file_id, event_num, active_boards)

            pids = get_gigaiwaki_processes()

            print('Latch up DAQ enable...')
            run_adalm_control(adalm_serial_daq_enable, latch=1)

            print('Resetting counters...') # input pulse-like signal
            run_adalm_control(adalm_serial_counter_reset, latch=1)
            time.sleep(0.1)
            run_adalm_control(adalm_serial_counter_reset, latch=0)

            start_time = time.time()

            print('Creating info files...')
            make_info_file(config_path, period_id, file_id, active_boards)

            # Wait for gigaiwaki processes to finish
            check_process_termination(pids)

            print("Kill gigaiwaki processes...")
            kill_gigaiwaki_processes(pids)

            end_time = time.time()
            
            print('Updating info files with end time...')
            update_info_file(period_id, file_id, end_time, active_boards)
            dt = datetime.fromtimestamp(end_time)
            rate_file_path = dt.strftime(f"{RATEPATH}/%Y%m%d")
            write_rate_log(rate_file_path, start_time, end_time, event_num)
            
            file_id += 1

        except KeyboardInterrupt:
            print('Keyboard interrupt received. Stopping DAQ...')
            run_daq_killer()
            break

    print('Deactivating Latch Up Detection...')
    run_set_latch_up_detect(config_path, io=0)

    print('Deactivating Regulator...')
    run_set_ap(config_path, io=0)
        
def main():
    print_header()
    args = arg_parser()
    config_path = args.config
    file_num = args.file_num
    event_num = args.event_num
    calin = args.calin

    print('--- Arguments ---')
    print('Config file name : ' + config_path)
    print('File number in a period : ' + str(file_num))
    print('Event number in a file : ' + str(event_num))
    if calin:
        print('Calibration input : IP = ' + calin[0] + ', channel = ' + calin[1])

    # Create new period
    while True:
        period = create_new_period()
        print('New period created : per' + str(period).zfill(4))
        run_daq(config_path, period, file_num, event_num, calin)
        exit()

if __name__ == '__main__':
    main()