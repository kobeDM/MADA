#!/usr/bin/env python3

import json
import os
import threading
import time
from datetime import datetime

from mada_adalm_control import run_adalm_control, get_adalm_serial, get_adalm_mask, AdalmError

MADAHOME = os.environ['MADAHOME']
RUN_DIR = MADAHOME + '/run'

VETO_INDEX = 2
VETO_LOG = RUN_DIR + '/veto.log'
VETO_STATE = RUN_DIR + '/veto.state'
RELEASE_RETRY_INTERVAL = 10.0  # sec


def get_veto_role(config_path):
    """(serial, DIO mask) of the veto line, or None when MADALM_2 is not configured."""
    with open(config_path, 'r') as f:
        config_load = json.load(f)

    entry = config_load['ADALM'].get('MADALM_' + str(VETO_INDEX))
    if entry is None or entry.get('active', 1) != 1:
        return None
    return get_adalm_serial(config_load, VETO_INDEX), get_adalm_mask(config_load, VETO_INDEX)


def veto_failed(state_path=VETO_STATE):
    """True when the veto owner reported a line it could not release."""
    try:
        with open(state_path, 'r') as f:
            return bool(json.load(f).get('failed', False))
    except (OSError, ValueError):
        return False


class SoftwareVeto:
    """Owner of the software-veto DIO line (active high) toward the external
    scaler. begin() returns immediately (the assert runs in a background
    thread) so the caller can start the LV reset at once; end() waits for it
    and releases the line. A line that cannot be released zeroes the scaler
    live time, so it is reported through the state file and retried."""

    def __init__(self, config_path, log_path=VETO_LOG, state_path=VETO_STATE):
        role = get_veto_role(config_path)
        self.enabled = role is not None
        self.serial, self.mask = role if role else (None, None)
        self.log_path = log_path
        self.state_path = state_path
        self.failed = False
        self._thread = None
        self._active = False
        self._pending_release = False
        self._last_retry = 0.0

        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        os.makedirs(os.path.dirname(state_path), exist_ok=True)

    def _log(self, text):
        now = time.time()
        stamp = datetime.fromtimestamp(now).isoformat(timespec='milliseconds')
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f'{now:.3f} {stamp} {text}\n')

    def _write_state(self):
        state = {'failed': self.failed, 'asserted': self._active or self._pending_release, 'time': time.time()}
        tmp = self.state_path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(state, f)
        os.replace(tmp, self.state_path)

    def _set(self, level):
        run_adalm_control(self.serial, latch=level, mask=self.mask, analog=False)

    def _try_release(self):
        self._last_retry = time.time()
        try:
            self._set(0)
        except AdalmError as e:
            self._pending_release = True
            self.failed = True
            print(f'[software_veto] ERROR: release failed ({e}); retrying every {RELEASE_RETRY_INTERVAL:.0f} s.')
            self._log('release-failed')
            self._write_state()
            return False

        self._pending_release = False
        self.failed = False
        self._log('release')
        self._write_state()
        return True

    def initialize(self):
        """Drive the line low explicitly; a floating line may read as veto."""
        if not self.enabled:
            print('[software_veto] MADALM_2 not configured; software veto disabled.')
            return
        self._pending_release = False
        if self._try_release():
            self._log('init low')

    def _assert(self, cause):
        try:
            self._set(1)
            self._log(f'assert {cause}')
        except AdalmError as e:
            print(f'[software_veto] WARNING: assert failed ({e}); continuing without veto.')
            self._log(f'assert-failed {cause}')

    def begin(self, cause):
        if not self.enabled or self._active:
            return
        self._active = True
        self._write_state()
        self._thread = threading.Thread(target=self._assert, args=(cause,), daemon=True)
        self._thread.start()

    def end(self):
        if not self.enabled or not self._active:
            return
        self._thread.join()
        self._active = False
        self._try_release()

    def retry_release(self):
        """Call periodically: retries a failed release at a fixed interval."""
        if self._pending_release and time.time() - self._last_retry >= RELEASE_RETRY_INTERVAL:
            self._try_release()

    def shutdown(self):
        """Leave the line low (one attempt); a failure stays in the state file."""
        if not self.enabled:
            return
        if self._thread is not None:
            self._thread.join()
        if self._active or self._pending_release:
            self._active = False
            self._try_release()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Set the software veto line manually (1: veto, 0: release). For testing only; the autoreset monitor owns the line.')
    parser.add_argument('level', type=int, choices=[0, 1])
    parser.add_argument('-c', '--config', default='MADA_config.json')
    args = parser.parse_args()

    veto = SoftwareVeto(args.config)
    if not veto.enabled:
        print('MADALM_2 not configured.')
        return
    veto._set(args.level)
    veto._log('manual ' + ('assert' if args.level else 'release'))

if __name__ == '__main__':
    main()
