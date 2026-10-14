#!/usr/bin/env python3

import sys
import argparse
import time

from mada_kill_modules import run_kill_modules
from mada_kill_adalms import run_kill_adalms
from mada_config import load_config, active_boards, ConfigError
from mada_adalm_roles import daq_roles, ROLE_DAQ_ENABLE, ROLE_COUNTER_RESET
from mada_adalm_runner import run_adalm_control, AdalmError
from mada_daq_killer import run_daq_killer
from mada_encoder_power import run_encoder_power_up, run_encoder_power_down
from mada_software_veto import veto_failed
from mada_daemon import daemonize, install_sigterm_handler, remove_pidfile, switch_log
from mada_autoreset_ctl import ensure_autoreset_running, MonitorError
from mada_run_logger import RunLogger
from mada_gigaiwaki import start_readers, kill_readers, GigaIwakiError
from mada_progress import ProgressMonitor

DRAIN_WAIT = 0.2  # sec, keep readers attached after DAQ enable falls, then kill them

def print_header():
    print('*********************************************************')
    print('*** mada.py                                           ***')
    print('*** Micacle Argon DAQ (http://github.com/kobeDM/MADA) ***')
    print('*** Author      : R.Namai (2026 Apl.)                 ***')
    print('*********************************************************')

def arg_parser():
    parser = argparse.ArgumentParser(description='Micacle Argon DAQ (MADA)')
    parser.add_argument('-c', '--config', help='config file name', default='MADA_config.json')
    parser.add_argument('-f', '--file_num', help='File number in a period', default=512, type=int)
    parser.add_argument('-n', '--event_num', help='Event number in a file', default=1000, type=int)
    parser.add_argument('-d', '--daemon', action='store_true', help='Run in the background, detached from the terminal')
    parser.add_argument('--calin', nargs=2, type=str, help='Calibration input: [IP] [channel (0-127)]', default=None)
    args = parser.parse_args()
    return args

def run_period(config_path, period_id, file_num, event_num, active_boards,
               adalm_serial_daq_enable, adalm_serial_counter_reset,
               adalm_mask_daq_enable, adalm_mask_counter_reset):
    logger = RunLogger(config_path, period_id)

    for file_id in range(file_num):
        if not ensure_autoreset_running(config_path):
            raise MonitorError('regulator autoreset monitor is not running')
        if veto_failed():
            raise AdalmError('software veto could not be released (see run/veto.state); stopping')
        print(f'Creating file {file_id} with {event_num} events...')

        print('Killing ADALM processes...')
        run_kill_adalms()

        # DAQ enable is low here: it was lowered when the previous file ended
        # (or by run_daq before the first file), so nothing is acquired
        # while the readers start and the counters are reset.
        # Readers that fail to come up are restarted one by one here; the
        # counter reset and DAQ enable below then go to all boards together.
        print('Running gigaiwaki (waiting for data flushing)...')
        mada_files = logger.mada_file_paths(file_id, active_boards)
        procs = start_readers(event_num, active_boards, mada_files)

        print('Resetting counters...')
        run_adalm_control(adalm_serial_counter_reset, latch=1, width=0.1,
                          mask=adalm_mask_counter_reset)

        print('Latch up DAQ enable...')
        run_adalm_control(adalm_serial_daq_enable, latch=1, mask=adalm_mask_daq_enable)

        start_time = time.time()

        print('Creating info files...')
        logger.write_info_start(file_id, active_boards, start_time)

        # Wait for gigaiwaki processes to finish
        ProgressMonitor(mada_files, event_num).wait_for_any_exit(procs)

        # Lower DAQ enable before anything else so no event is taken while
        # the readers are being stopped.
        print('Latch down DAQ enable...')
        run_adalm_control(adalm_serial_daq_enable, latch=0, mask=adalm_mask_daq_enable)
        end_time = time.time()

        time.sleep(DRAIN_WAIT)

        print("Kill gigaiwaki processes...")
        kill_readers(procs)

        print('Updating info files with end time...')
        logger.finalize_file(file_id, active_boards, end_time, start_time)


def run_daq(config_path, file_num, event_num, first_period, daemon, calin=None):
    config_load = load_config(config_path)
    boards = active_boards(config_load)
    if calin:
        boards = [(board_id, ip) for board_id, ip in boards if ip == calin[0]]
    else:
        for board_id, ip in boards:
            print(f'Starting DAQ for board {board_id} at IP {ip}')

    run_kill_modules()
    roles = daq_roles(config_load)
    adalm_serial_daq_enable, adalm_mask_daq_enable = roles[ROLE_DAQ_ENABLE]
    adalm_serial_counter_reset, adalm_mask_counter_reset = roles[ROLE_COUNTER_RESET]

    run_encoder_power_up(config_path, require_monitor=True)

    print('DAQ is running... Press Ctrl+C to stop.')
    try:
        print('Latch down DAQ enable (initial)...')
        run_adalm_control(adalm_serial_daq_enable, latch=0, mask=adalm_mask_daq_enable)

        period = first_period
        while True:
            print('New period created : per' + str(period).zfill(4))
            run_period(config_path, period, file_num, event_num, boards,
                       adalm_serial_daq_enable, adalm_serial_counter_reset,
                       adalm_mask_daq_enable, adalm_mask_counter_reset)
            period = RunLogger.new_period()
            if daemon:
                switch_log(period)
    except KeyboardInterrupt:
        print('Keyboard interrupt received. Stopping DAQ...')
        run_daq_killer(config_path)
        raise
    except (GigaIwakiError, AdalmError, MonitorError) as e:
        print(f'FATAL: {e}. Stopping DAQ...')
        run_daq_killer(config_path)
        raise
    finally:
        # Close the scaler period: it is updated on the falling edge of DAQ enable.
        try:
            run_adalm_control(adalm_serial_daq_enable, latch=0, mask=adalm_mask_daq_enable)
        except AdalmError as e:
            print(f'WARNING: could not latch down DAQ enable on exit ({e}).')
        run_encoder_power_down(config_path)

def main():
    args = arg_parser()
    config_path = args.config
    file_num = args.file_num
    event_num = args.event_num
    calin = args.calin

    # Allocate the starting period before daemonizing, since the per-period
    # log file name (<run_name>_<period>.log) needs to be known up front.
    first_period = RunLogger.new_period()

    if args.daemon:
        daemonize(first_period)

    print_header()
    install_sigterm_handler()

    print('--- Arguments ---')
    print('Config file name : ' + config_path)
    print('File number in a period : ' + str(file_num))
    print('Event number in a file : ' + str(event_num))
    if calin:
        print('Calibration input : IP = ' + calin[0] + ', channel = ' + calin[1])

    try:
        run_daq(config_path, file_num, event_num, first_period, args.daemon, calin)
    except KeyboardInterrupt:
        print('DAQ stopped by user.')
    except (GigaIwakiError, AdalmError, MonitorError, ConfigError) as e:
        print(f'DAQ stopped due to error: {e}')
        sys.exit(1)
    finally:
        if args.daemon:
            remove_pidfile()

if __name__ == '__main__':
    main()