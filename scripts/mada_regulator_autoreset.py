#!/usr/bin/env python3

import os
import glob
import json
import time
import argparse
import threading

from mada_set_ap import run_set_ap

CONFIG = './MADA_config.json'
MONITOR_DIR = '/nadb/nadb65/status/mpod/regulator_autoreset'
POLL_INTERVAL = 1.0
RESET_SETTLE = 1.0  # AP off-time before turning back on, for hardware settling

def arg_parser():
    parser = argparse.ArgumentParser(description='Watch MPOD over-current logs and reset the regulator (AP 0->1) on any board mapped to the module that reports a new over-limit line.')
    parser.add_argument('-c', '--config', default=CONFIG)
    args = parser.parse_args()
    return args

def get_module_boards(config_path):
    with open(config_path, 'r') as file:
        config_load = json.load(file)

    module_boards = {}
    for name, data in config_load.get('gigaIwaki', {}).items():
        if data.get('active') != 1:
            continue

        module = data.get('module')
        if module is None:
            continue

        module_boards.setdefault(module, []).append((name, data['IP']))
    return module_boards


class RegulatorAutoresetMonitor:
    """Watches per-module MPOD over-current logs under MONITOR_DIR and resets
    the regulator (AP 0->1) for the boards on a module as soon as a new
    over-limit line is appended (the log only ever records over-limit
    samples, so any new line is itself the trigger)."""

    def __init__(self, config_path, monitor_dir=MONITOR_DIR, poll_interval=POLL_INTERVAL):
        self.config_path = config_path
        self.monitor_dir = monitor_dir
        self.poll_interval = poll_interval
        self.module_boards = get_module_boards(config_path)

        self._tracked = {}
        self._stop_event = threading.Event()
        self._thread = None

    def _latest_log_path(self, module):
        pattern = os.path.join(self.monitor_dir, f'Module-{module}_*.log')
        matches = sorted(glob.glob(pattern))
        return matches[-1] if matches else None

    def _prime(self):
        for module in self.module_boards:
            path = self._latest_log_path(module)
            self._tracked[module] = {
                'path': path,
                'offset': os.path.getsize(path) if path else 0,
                'carry': b'',
            }

    def _new_lines(self, module):
        state = self._tracked[module]
        path = self._latest_log_path(module)
        if path is None:
            return []

        if path != state['path']:
            # A file we haven't tracked before (first appearance after start,
            # or the daily rotation) has no history to skip; read it from 0.
            state['path'] = path
            state['offset'] = 0
            state['carry'] = b''

        try:
            with open(path, 'rb') as f:
                f.seek(state['offset'])
                chunk = f.read()
        except FileNotFoundError:
            return []

        if not chunk:
            return []

        state['offset'] += len(chunk)
        *complete, state['carry'] = (state['carry'] + chunk).split(b'\n')
        return [line.decode(errors='replace') for line in complete if line]

    def _reset_module(self, module):
        for board_id, ip in self.module_boards[module]:
            print(f'[regulator_autoreset] Over-limit on Module-{module}: resetting AP for {board_id} (IP: {ip})...')
            run_set_ap(self.config_path, io=0, target_ip=ip)
            time.sleep(RESET_SETTLE)
            run_set_ap(self.config_path, io=1, target_ip=ip)

    def _run(self):
        self._prime()
        while not self._stop_event.is_set():
            for module in self.module_boards:
                if self._new_lines(module):
                    self._reset_module(module)
            self._stop_event.wait(self.poll_interval)

    def start(self):
        if not self.module_boards:
            print('[regulator_autoreset] No board has a "module" mapping in the config; monitoring disabled.')
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread is None:
            return

        self._stop_event.set()
        self._thread.join()
        self._thread = None


def main():
    print('*** mada_regulator_autoreset.py start ***')

    args = arg_parser()
    monitor = RegulatorAutoresetMonitor(args.config)
    monitor.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Keyboard interrupt received. Stopping monitor...')
    finally:
        monitor.stop()

    print('*** mada_regulator_autoreset.py end ***')

if __name__ == '__main__':
    main()
