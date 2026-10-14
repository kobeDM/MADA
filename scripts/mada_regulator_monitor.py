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
from mada_run_state import read_run_state
from mada_set_ap import run_set_ap
from mada_warning_log import append_warning, event_message, WARNING_LOG_NAME

MONITOR_DIR = '/nadb/nadb65/status/mpod/regulator_autoreset'
POLL_INTERVAL = 1.0
RESET_SETTLE = 1.0  # AP off-time before turning back on, for hardware settling
VETO_MARGIN = 0.5   # sec, veto hold time after AP on (ASIC can measure immediately)
AP_ON_RETRIES = 3
LOG_SOURCE = 'LV'  # source column of this monitor's records in the period warning log


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
        if veto is not None:
            veto.on_event = self._on_veto_event

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

    @staticmethod
    def _record(level, kind, **fields):
        """Append a record to the warning log of the period the DAQ is writing
        now; nothing is written when no DAQ is running."""
        state = read_run_state()
        if state is None:
            return
        append_warning(os.path.join(state['period_dir'], WARNING_LOG_NAME), state['file_id'],
                       LOG_SOURCE, event_message(level, kind, **fields))

    def _on_veto_event(self, text):
        word = text.split()[0] if text.split() else 'event'
        level = 'WARNING' if word.endswith('failed') else 'INFO'
        self._record(level, 'veto_' + word.replace('-', '_'), detail=text.replace(' ', '_'))

    def _ap_on_with_retry(self, board_id, ip):
        for attempt in range(1, AP_ON_RETRIES + 1):
            try:
                run_set_ap(self.config_path, io=1, target_ip=ip, ensure=False)
                self._record('INFO', 'ap_on', board=board_id)
                return
            except Exception as e:
                print(f'[regulator_autoreset] WARNING: AP on failed for {board_id} ({e}), attempt {attempt}/{AP_ON_RETRIES}')
                self._record('WARNING', 'ap_on_failed', board=board_id, attempt=attempt)
                time.sleep(1.0)
        print(f'[regulator_autoreset] ERROR: {board_id} (IP: {ip}) was left with AP OFF.')
        self._record('ERROR', 'ap_left_off', board=board_id)

    def _reset_boards(self, module, boards):
        for board_id, ip in boards:
            print(f'[regulator_autoreset] Over-limit on Module-{module}: resetting AP for {board_id} (IP: {ip})...')
            self._record('INFO', 'ap_off', board=board_id)
            try:
                run_set_ap(self.config_path, io=0, target_ip=ip, ensure=False)
            except Exception as e:
                print(f'[regulator_autoreset] ERROR: AP off failed for {board_id} ({e}); trying AP on anyway.')
                self._record('ERROR', 'ap_off_failed', board=board_id)
            time.sleep(RESET_SETTLE)
            self._ap_on_with_retry(board_id, ip)

    def _fired_modules(self):
        """{module: new over-limit lines} for the modules that reported any."""
        fired = {}
        for module in self.module_boards:
            lines = self._new_lines(module)
            if lines:
                fired[module] = lines
        return fired

    def _reset_targets(self, fired):
        """Boards to reset per module. A board whose AP is off is left alone
        (resetting it would switch it on); an unreadable state is treated as on."""
        targets = {}
        for module in fired:
            boards = []
            for board_id, ip in self.module_boards[module]:
                if get_ap_state(ip) is False:
                    print(f'[regulator_autoreset] {board_id} (IP: {ip}) has AP off; not resetting.')
                    self._record('INFO', 'ap_off_skip', board=board_id)
                    continue
                boards.append((board_id, ip))
            if boards:
                targets[module] = boards
        return targets

    def _handle_over_limit(self, fired):
        # AP off starts at once; the veto assert runs in parallel (slower)
        # and is held until no new over-limit line appears after the margin.
        for module, lines in fired.items():
            self._record('WARNING', 'over_limit', module=module, lines=len(lines),
                         last='"' + lines[-1] + '"')

        targets = self._reset_targets(fired)
        if not targets:
            return

        started = time.time()
        resets = 0
        self._record('WARNING', 'lv_reset_start', modules=','.join(str(m) for m in targets),
                     boards=','.join(b for boards in targets.values() for b, _ in boards))

        if self.veto:
            self.veto.begin('lv-reset module=' + ','.join(str(m) for m in targets))

        try:
            while targets:
                for module, boards in targets.items():
                    self._reset_boards(module, boards)
                    resets += len(boards)
                self._stop_event.wait(VETO_MARGIN)
                if self._stop_event.is_set():
                    break
                targets = self._reset_targets(self._fired_modules())
        finally:
            if self.veto:
                self.veto.end()
            self._record('WARNING', 'lv_reset_end', duration=f'{time.time() - started:.1f}', resets=resets)

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
