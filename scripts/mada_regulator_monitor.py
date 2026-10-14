#!/usr/bin/env python3

"""Watches the MPOD over-current logs and resets the regulators (AP 0->1) of
the boards on the affected module, driving the software veto meanwhile."""

import glob
import os
import threading
import time
import traceback

from mada_ap_state import get_ap_state
from mada_config import load_config, module_boards
from mada_set_ap import run_set_ap

MONITOR_DIR = '/nadb/nadb65/status/mpod/regulator_autoreset'
POLL_INTERVAL = 1.0
RESET_SETTLE = 1.0  # AP off-time before turning back on, for hardware settling
VETO_MARGIN = 0.5   # sec, veto hold time after AP on (ASIC can measure immediately)
AP_ON_RETRIES = 3


class RegulatorAutoresetMonitor:
    """Watches per-module MPOD over-current logs under MONITOR_DIR and resets
    the regulator (AP 0->1) for the boards on a module as soon as a new
    over-limit line is appended (the log only ever records over-limit
    samples, so any new line is itself the trigger)."""

    def __init__(self, config_path, monitor_dir=MONITOR_DIR, poll_interval=POLL_INTERVAL, veto=None):
        self.config_path = config_path
        self.monitor_dir = monitor_dir
        self.poll_interval = poll_interval
        self.module_boards = module_boards(load_config(config_path))
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
