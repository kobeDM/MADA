#!/usr/bin/env python3

import os
import sys
import glob
import json
import time
import signal
import argparse
import threading
import traceback

from mada_set_ap import run_set_ap, get_ap_state
from mada_software_veto import SoftwareVeto
from mada_daemon import detach
from mada_autoreset_ctl import (RUN_DIR, PIDFILE_PATH, CONFIG_RECORD_PATH, LOG_PATH,
                                monitor_pid, acquire_lock)

CONFIG = './MADA_config.json'
MONITOR_DIR = '/nadb/nadb65/status/mpod/regulator_autoreset'
POLL_INTERVAL = 1.0
RESET_SETTLE = 1.0  # AP off-time before turning back on, for hardware settling
VETO_MARGIN = 0.5   # sec, veto hold time after AP on (ASIC can measure immediately)
AP_ON_RETRIES = 3
IDLE_EXIT_DEFAULT = 600.0  # sec, exit after all boards had AP off for this long
IDLE_CHECK_INTERVAL = 30.0  # sec

def arg_parser():
    parser = argparse.ArgumentParser(description='Watch MPOD over-current logs and reset the regulator (AP 0->1) on any board mapped to the module that reports a new over-limit line, driving the software veto meanwhile. Run it once and keep it running, independently of mada.py.')
    parser.add_argument('-c', '--config', default=CONFIG)
    parser.add_argument('-d', '--daemon', action='store_true', help='Run in the background (log: run/mada_autoreset.log)')
    parser.add_argument('--stop', action='store_true', help='Stop the running background monitor')
    parser.add_argument('--idle-exit', type=float, default=IDLE_EXIT_DEFAULT, help='Exit after every active board has had AP off for this many seconds (0: never; default 600)')
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

    def __init__(self, config_path, monitor_dir=MONITOR_DIR, poll_interval=POLL_INTERVAL, veto=None):
        self.config_path = config_path
        self.monitor_dir = monitor_dir
        self.poll_interval = poll_interval
        self.module_boards = get_module_boards(config_path)
        self.veto = veto

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

    def _ap_on_with_retry(self, board_id, ip):
        for attempt in range(1, AP_ON_RETRIES + 1):
            try:
                run_set_ap(self.config_path, io=1, target_ip=ip, ensure=False)
                return
            except Exception as e:
                print(f'[regulator_autoreset] WARNING: AP on failed for {board_id} ({e}), attempt {attempt}/{AP_ON_RETRIES}')
                time.sleep(1.0)
        print(f'[regulator_autoreset] ERROR: {board_id} (IP: {ip}) was left with AP OFF.')

    def _reset_boards(self, module, boards):
        for board_id, ip in boards:
            print(f'[regulator_autoreset] Over-limit on Module-{module}: resetting AP for {board_id} (IP: {ip})...')
            try:
                run_set_ap(self.config_path, io=0, target_ip=ip, ensure=False)
            except Exception as e:
                print(f'[regulator_autoreset] ERROR: AP off failed for {board_id} ({e}); trying AP on anyway.')
            time.sleep(RESET_SETTLE)
            self._ap_on_with_retry(board_id, ip)

    def _fired_modules(self):
        return [module for module in self.module_boards if self._new_lines(module)]

    def _reset_targets(self, fired):
        """Boards to reset per module. A board whose AP is off is left alone
        (resetting it would switch it on); an unreadable state is treated as on."""
        targets = {}
        for module in fired:
            boards = []
            for board_id, ip in self.module_boards[module]:
                if get_ap_state(ip) is False:
                    print(f'[regulator_autoreset] {board_id} (IP: {ip}) has AP off; not resetting.')
                    continue
                boards.append((board_id, ip))
            if boards:
                targets[module] = boards
        return targets

    def _handle_over_limit(self, fired):
        # AP off starts at once; the veto assert runs in parallel (slower)
        # and is held until no new over-limit line appears after the margin.
        targets = self._reset_targets(fired)
        if not targets:
            return

        if self.veto:
            self.veto.begin('lv-reset module=' + ','.join(str(m) for m in targets))

        try:
            while targets:
                for module, boards in targets.items():
                    self._reset_boards(module, boards)
                self._stop_event.wait(VETO_MARGIN)
                if self._stop_event.is_set():
                    break
                targets = self._reset_targets(self._fired_modules())
        finally:
            if self.veto:
                self.veto.end()

    def _run(self):
        self._prime()
        while not self._stop_event.is_set():
            try:
                fired = self._fired_modules()
                if fired:
                    self._handle_over_limit(fired)
                if self.veto:
                    self.veto.retry_release()
            except Exception:
                traceback.print_exc()
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


def stop_daemon():
    pid = monitor_pid()
    if pid is None:
        print('No running autoreset monitor found.')
        return
    print(f'Sending SIGTERM to PID {pid}...')
    os.kill(pid, signal.SIGTERM)


def all_boards_ap_off(boards):
    return all(get_ap_state(ip) is False for ip in boards)


def main():
    args = arg_parser()

    if args.stop:
        stop_daemon()
        return

    if monitor_pid() is not None:
        print('An autoreset monitor is already running.')
        sys.exit(1)

    config_path = os.path.abspath(args.config)
    if not os.path.isfile(config_path):
        print(f'Error: config file {config_path} not found.')
        sys.exit(1)

    if args.daemon:
        detach(LOG_PATH)

    lock = acquire_lock(wait=5.0)
    if lock is None:
        print('Another autoreset monitor holds the lock; exiting.')
        sys.exit(0)

    with open(PIDFILE_PATH, 'w') as f:
        f.write(str(os.getpid()))
    with open(CONFIG_RECORD_PATH, 'w') as f:
        f.write(config_path)

    def _handle_sigterm(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_sigterm)

    print('*** mada_regulator_autoreset.py start ***')
    veto = SoftwareVeto(config_path)
    veto.initialize()
    monitor = RegulatorAutoresetMonitor(config_path, veto=veto)
    monitor.start()

    boards = [ip for boards_ in monitor.module_boards.values() for _, ip in boards_]
    off_since = None
    try:
        while True:
            time.sleep(IDLE_CHECK_INTERVAL)
            if args.idle_exit <= 0 or not boards:
                continue
            if all_boards_ap_off(boards):
                off_since = off_since or time.time()
                if time.time() - off_since >= args.idle_exit:
                    print(f'All boards have had AP off for {args.idle_exit:.0f} s; exiting.')
                    break
            else:
                off_since = None
    except KeyboardInterrupt:
        print('Stopping monitor...')
    finally:
        monitor.stop()
        veto.shutdown()
        for path in (PIDFILE_PATH, CONFIG_RECORD_PATH):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    print('*** mada_regulator_autoreset.py end ***')

if __name__ == '__main__':
    main()
