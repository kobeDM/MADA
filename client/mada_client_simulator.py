#!/usr/bin/env python3

"""A simulated mada.py for developing the DAQ client and the web server
without hardware. Same command line as mada.py; it writes the same files
(pidfile, mada_run.json, mada_progress.json, perNNNN/*.info, warnings.log,
mada_last_exit.json) but acquires nothing.

Scenarios, from the environment: MADA_SIM_FILE_SEC (seconds per file),
MADA_SIM_FAIL_AFTER (stop with an error after this many files),
MADA_SIM_LAG (the second board lags), MADA_SIM_INVALID_FILE (that file number
comes out invalid), MADA_SIM_SHUTDOWN_SEC (duration of the shutdown)."""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'scripts'))

from mada_daemon import daemonize, install_sigterm_handler, remove_pidfile, run_name
from mada_errors import MadaError
from mada_run_logger import RunLogger
from mada_scaler import STATE_PATH as SCALER_STATE_PATH
from mada_run_state import (clear_last_exit, clear_progress, clear_run_state, clear_stop_request, publish_progress,
                            publish_run_state, set_period, soft_stop_requested, write_json, write_last_exit)
from mada_warning_log import WARNING_LOG_NAME, append_warning, event_message

STEP = 0.25  # sec between progress updates
EVENT_BYTES = 2000  # bytes per simulated event


def env_number(name, default, cast=float):
    return cast(os.environ.get(name, default))


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default='MADA_config.json')
    parser.add_argument('-f', '--file_num', type=int, default=512)
    parser.add_argument('-n', '--event_num', type=int, default=1000)
    parser.add_argument('-d', '--daemon', action='store_true')
    parser.add_argument('--sci', action='store_true')
    return parser.parse_args()


def load_boards(path):
    try:
        with open(path) as f:
            config = json.load(f)
        boards = [(name, data) for name, data in config['gigaIwaki'].items() if data.get('active') == 1]
    except (OSError, ValueError, KeyError, AttributeError) as e:
        print(f"Error: cannot use config file '{path}': {e}")
        sys.exit(1)
    if not boards:
        print('Error: invalid board settings: no board has active == 1')
        sys.exit(1)
    return boards


def write_info(period_dir, file_id, boards, start, end, counts, invalid):
    for name, data in boards:
        runinfo = {'start': start, 'end': end, 'size': str(counts[name] * EVENT_BYTES)}
        if invalid:
            runinfo.update({'valid': False, 'invalid_reason': invalid})
        with open(f'{period_dir}/{name}_{file_id:04d}.info', 'w', encoding='utf-8') as f:
            json.dump({'gigaIwaki': data, 'runinfo': runinfo}, f, indent=4)


def acquire_file(period_dir, file_id, boards, event_num, file_sec, lag, extra):
    """One simulated file; returns (start, end, counts)."""
    publish_run_state(period_dir, file_id, file_started_at=None, **extra)
    start = time.time()
    publish_run_state(period_dir, file_id, file_started_at=start, **extra)
    counts = {name: 0 for name, _ in boards}
    lagging = False
    while True:
        done = min(1.0, (time.time() - start) / file_sec)
        for i, (name, _) in enumerate(boards):
            counts[name] = int(event_num * done * (0.9 if lag and i == 1 and done < 1 else 1.0))
        if lag and done < 1 and not lagging:
            lagging = True
            append_warning(f'{period_dir}/{WARNING_LOG_NAME}', file_id, boards[1][0],
                           event_message('WARNING', 'board_lag', events=counts[boards[1][0]], lead=event_num))
        publish_progress(period_dir, file_id, event_num, counts, [boards[1][0]] if lagging and done < 1 else [])
        if done >= 1:
            break
        time.sleep(STEP)
    clear_progress()
    return start, time.time(), counts


def write_scaler_state(state, period):
    write_json(SCALER_STATE_PATH, {'state': state, 'period': period, 'pid': None, 'host': 'sim', 'time': time.time()})


def run_simulation(args, boards, first_period):
    file_sec = env_number('MADA_SIM_FILE_SEC', 3.0)
    fail_after = env_number('MADA_SIM_FAIL_AFTER', 0, int)
    lag = os.environ.get('MADA_SIM_LAG') == '1'
    invalid_file = env_number('MADA_SIM_INVALID_FILE', -1, int)
    extra = {'run': run_name(), 'file_num': args.file_num, 'event_num': args.event_num, 'sci': args.sci,
             'boards': [{'id': name, 'ip': data.get('IP')} for name, data in boards]}
    period, taken = first_period, 0
    while True:
        logger = RunLogger(args.config, period)
        period_dir = logger.period_dir_abs()
        write_scaler_state('running', period)
        valid = 0
        for file_id in range(10 ** 6):
            if valid >= args.file_num:
                break
            if fail_after and taken >= fail_after:
                raise MadaError(f'simulated failure after {taken} files')
            start, end, counts = acquire_file(period_dir, file_id, boards, args.event_num, file_sec, lag,
                                              dict(extra, period=period, valid_files=valid))
            invalid = 'simulated reader exit' if file_id == invalid_file else None
            write_info(period_dir, file_id, boards, start, end, counts, invalid)
            valid += 0 if invalid else 1
            taken += 1
            if soft_stop_requested():
                raise KeyboardInterrupt
        write_scaler_state('stopped', period)
        period = RunLogger.new_period()


def main():
    args = arg_parser()
    boards = load_boards(args.config)
    first_period = RunLogger.new_period()
    set_period(first_period)
    if args.daemon:
        daemonize(first_period)
    install_sigterm_handler()
    clear_last_exit()
    clear_stop_request()
    print(f'Simulated DAQ with {len(boards)} boards')
    try:
        run_simulation(args, boards, first_period)
    except KeyboardInterrupt:
        print('DAQ stopped by user.')
        time.sleep(env_number('MADA_SIM_SHUTDOWN_SEC', 2.0))
        clear_run_state()
        write_scaler_state('stopped', first_period)
        write_last_exit('stopped')
    except MadaError as e:
        print(f'DAQ stopped due to error: {e}')
        clear_run_state()
        write_scaler_state('stopped', first_period)
        write_last_exit('error', str(e))
        sys.exit(1)
    finally:
        remove_pidfile()


if __name__ == '__main__':
    main()
