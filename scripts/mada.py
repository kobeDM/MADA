#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
import json
import time

from mada_kill_modules import run_kill_modules
from mada_kill_adalms import run_kill_adalms
from mada_adalm_control import run_adalm_control, get_adalm_serial
from mada_daq_killer import run_daq_killer
from mada_encoder_power import run_encoder_power_up, run_encoder_power_down
from mada_regulator_autoreset import RegulatorAutoresetMonitor
from mada_daemon import daemonize, install_sigterm_handler, remove_pidfile, switch_log
from mada_rate_log import write_rate_log

HOME     = os.environ["HOME"]
RATEPATH = HOME + "/rate"

MADAHOME = os.environ['MADAHOME']
MADA_IWAKI = MADAHOME + "/bin/MadaIwaki"

UPIC_FOOTER = b'uPIC'
PROGRESS_POLL_INTERVAL = 0.2

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

def load_config(config_path):
    with open(config_path, 'r') as f:
        config_load = json.load(f)
    return config_load

def get_active_boards(config_path):
    with open(config_path, 'r') as file:
        config_load = json.load(file)

    active_boards = []
    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active'] == 1:
            active_boards.append((x, config_load['gigaIwaki'][x]['IP']))
    return active_boards


class RunLogger:
    """Owns per-period file paths and the .info/.mada/rate log bookkeeping."""

    def __init__(self, config_path, period_id):
        self.config_path = config_path
        self.period_id = period_id

    @staticmethod
    def new_period() -> int:
        period = 0
        while os.path.exists('per' + str(period).zfill(4)):
            period += 1
        os.makedirs('per' + str(period).zfill(4))
        return period

    def _period_dir(self):
        return 'per' + str(self.period_id).zfill(4)

    def _info_file_path(self, file_id, board_id):
        return f'{self._period_dir()}/{board_id}_{str(file_id).zfill(4)}.info'

    def mada_file_paths(self, file_id, active_boards):
        return {
            board_id: f'{self._period_dir()}/{board_id}_{str(file_id).zfill(4)}.mada'
            for board_id, ip in active_boards
        }

    def write_info_start(self, file_id, active_boards, start_time):
        with open(self.config_path, 'r') as file:
            config_load = json.load(file)

        for board_id, ip in active_boards:
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

                    with open(self._info_file_path(file_id, board_id), mode='wt', encoding='utf-8') as out_file:
                        json.dump(output_data, out_file, ensure_ascii=False, indent=4)

                    break

    def write_info_end(self, file_id, active_boards, end_time):
        sizes_by_board = {}
        for board_id, ip in active_boards:
            info_file_path = self._info_file_path(file_id, board_id)
            mada_file_path = f'{self._period_dir()}/{board_id}_{str(file_id).zfill(4)}.mada'

            mada_file_missing = not os.path.exists(mada_file_path)
            if mada_file_missing:
                file_size = 0
                print(f'WARNING: {mada_file_path} not found (connection failure suspected on {board_id})')
            else:
                file_size = os.path.getsize(mada_file_path)
            print('size= ', file_size, 'byte')
            sizes_by_board[board_id] = file_size

            with open(info_file_path, 'r', encoding='utf-8') as f:
                info_load = json.load(f)

            info_load.setdefault('runinfo', {})
            info_load['runinfo'].update({
                'end': end_time,
                'size': str(file_size)
            })
            if mada_file_missing:
                info_load['runinfo']['error'] = 'mada file not found (connection failure suspected)'

            with open(info_file_path, 'w', encoding='utf-8') as f:
                json.dump(info_load, f, ensure_ascii=False, indent=4)

        return sizes_by_board

    def write_rate_log(self, start_time, end_time, sizes):
        write_rate_log(RATEPATH, start_time, end_time, sizes)


def run_gigaiwaki(event_num, active_boards, mada_files):
    for board_id, ip in active_boards:
        cmd = f'{MADA_IWAKI} -n {event_num} -f {mada_files[board_id]} -i {ip}'
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_gigaiwaki_processes():
    result = subprocess.run(['pgrep', '-f', 'MadaIwaki'], stdout=subprocess.PIPE, text=True)
    pids = result.stdout.strip().split('\n')
    return [int(pid) for pid in pids if pid.isdigit()]


def is_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class ProgressMonitor:
    """Tracks and displays each board's live event count during acquisition,
    by tailing the growing .mada files for the 'uPIC' footer marker."""

    def __init__(self, mada_files, event_num, poll_interval=PROGRESS_POLL_INTERVAL):
        self.mada_files = mada_files
        self.event_num = event_num
        self.poll_interval = poll_interval

        self.board_ids = list(mada_files.keys())
        self.offsets = {board_id: 0 for board_id in self.board_ids}
        self.carries = {board_id: b'' for board_id in self.board_ids}
        self.counts = {board_id: 0 for board_id in self.board_ids}
        self.is_tty = sys.stdout.isatty()
        self._drawn = False

    @staticmethod
    def _count_new_footers(data, carry):
        # Prepend the tail of the previous chunk so a footer split across
        # two polls (e.g. "...uPI" | "C...") is still detected.
        buf = carry + data
        return buf.count(UPIC_FOOTER), buf[-(len(UPIC_FOOTER) - 1):]

    def poll(self):
        for board_id, path in self.mada_files.items():
            try:
                with open(path, 'rb') as f:
                    f.seek(self.offsets[board_id])
                    chunk = f.read()
            except FileNotFoundError:
                continue

            if not chunk:
                continue

            found, self.carries[board_id] = self._count_new_footers(chunk, self.carries[board_id])
            self.counts[board_id] += found
            self.offsets[board_id] += len(chunk)

    def render(self, final=False):
        # On a TTY, redraw the same lines in place every poll (cheap, bounded
        # size). Off a TTY (redirected to a file, e.g. --daemon), each poll
        # would otherwise append a fresh line and blow up the log file, so
        # only print once the counts are final.
        if self.is_tty:
            if self._drawn:
                sys.stdout.write(f'\x1b[{len(self.board_ids)}A')
            for board_id in self.board_ids:
                line = f'  {board_id}: {self.counts[board_id]:>6}/{self.event_num:<6} events stored'
                sys.stdout.write('\x1b[2K' + line + '\n')
            sys.stdout.flush()
            self._drawn = True
        elif final:
            for board_id in self.board_ids:
                line = f'  {board_id}: {self.counts[board_id]:>6}/{self.event_num:<6} events stored'
                print(line)
            sys.stdout.flush()

    def wait_for_any_exit(self, pids):
        """Poll and render while waiting for at least one gigaiwaki process
        to exit (matching the intended 'one board done -> stop all' policy)."""
        print('Waiting for gigaiwaki processes to finish...')
        process_num_org = len(pids)

        while True:
            self.poll()
            self.render()

            alive_pids = [p for p in pids if is_alive(p)]
            if len(alive_pids) != process_num_org:
                break
            time.sleep(self.poll_interval)

        # Catch any events written just before the processes were found to
        # have stopped, and print the final per-board counts.
        self.poll()
        self.render(final=True)


def kill_gigaiwaki_processes(pids):
    for pid in pids:
        try:
            os.kill(pid, 9)
            print(f'Killed process with PID: {pid}')
        except ProcessLookupError:
            print(f'Process with PID {pid} not found. It may have already terminated.')

def run_period(config_path, period_id, file_num, event_num, active_boards,
               adalm_serial_daq_enable, adalm_serial_counter_reset):
    logger = RunLogger(config_path, period_id)

    for file_id in range(file_num):
        print(f'Creating file {file_id} with {event_num} events...')

        print('Killing ADALM processes...')
        run_kill_adalms()

        print('Latch down DAQ enable...')
        run_adalm_control(adalm_serial_daq_enable, latch=0)

        print('Running gigaiwaki...')
        mada_files = logger.mada_file_paths(file_id, active_boards)
        run_gigaiwaki(event_num, active_boards, mada_files)

        pids = get_gigaiwaki_processes()

        print('Latch up DAQ enable...')
        run_adalm_control(adalm_serial_daq_enable, latch=1)

        print('Waiting data flushing...')
        time.sleep(1)

        print('Resetting counters...')
        run_adalm_control(adalm_serial_counter_reset, latch=1, width=0.1)

        start_time = time.time()

        print('Creating info files...')
        logger.write_info_start(file_id, active_boards, start_time)

        # Wait for gigaiwaki processes to finish
        ProgressMonitor(mada_files, event_num).wait_for_any_exit(pids)

        print("Kill gigaiwaki processes...")
        kill_gigaiwaki_processes(pids)

        end_time = time.time()

        print('Updating info files with end time...')
        sizes_by_board = logger.write_info_end(file_id, active_boards, end_time)
        sizes = [sizes_by_board[board_id] for board_id, ip in active_boards]
        logger.write_rate_log(start_time, end_time, sizes)


def run_daq(config_path, file_num, event_num, first_period, daemon, calin=None):
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

    run_encoder_power_up(config_path)
    regulator_monitor = RegulatorAutoresetMonitor(config_path)
    regulator_monitor.start()

    print('DAQ is running... Press Ctrl+C to stop.')
    try:
        period = first_period
        while True:
            print('New period created : per' + str(period).zfill(4))
            run_period(config_path, period, file_num, event_num, active_boards,
                       adalm_serial_daq_enable, adalm_serial_counter_reset)
            period = RunLogger.new_period()
            if daemon:
                switch_log(period)
    except KeyboardInterrupt:
        print('Keyboard interrupt received. Stopping DAQ...')
        run_daq_killer()
        raise
    finally:
        regulator_monitor.stop()
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
    finally:
        if args.daemon:
            remove_pidfile()

if __name__ == '__main__':
    main()