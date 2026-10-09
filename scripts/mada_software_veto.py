#!/usr/bin/env python3

import json
import threading
import time
from datetime import datetime

from mada_adalm_control import run_adalm_control, get_adalm_serial, get_adalm_mask, AdalmError

VETO_INDEX = 2
VETO_LOG = 'veto.log'


class SoftwareVeto:
    """Drives the software-veto DIO line (active high) of the ADALM toward
    the external scaler. begin() returns immediately (the assert runs in a
    background thread) so the caller can start the LV reset at once; end()
    waits for it and releases the line. A failed release sets `failed`,
    because a stuck veto silently zeroes the scaler live time."""

    def __init__(self, config_path, log_path=VETO_LOG):
        with open(config_path, 'r') as f:
            config_load = json.load(f)

        entry = config_load['ADALM'].get('MADALM_' + str(VETO_INDEX))
        self.enabled = entry is not None and entry.get('active', 1) == 1
        self.log_path = log_path
        self.failed = False
        self._thread = None
        self._active = False

        if self.enabled:
            self.serial = get_adalm_serial(config_load, VETO_INDEX)
            self.mask = get_adalm_mask(config_load, VETO_INDEX)
        else:
            self.serial = None
            self.mask = None

    def _log(self, text):
        now = time.time()
        stamp = datetime.fromtimestamp(now).isoformat(timespec='milliseconds')
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(f'{now:.3f} {stamp} {text}\n')

    def _set(self, level):
        run_adalm_control(self.serial, latch=level, mask=self.mask, analog=False)

    def initialize(self):
        """Drive the line low explicitly; a floating line may read as veto."""
        if not self.enabled:
            print('[software_veto] MADALM_2 not configured; software veto disabled.')
            return
        self._set(0)
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
        self._thread = threading.Thread(target=self._assert, args=(cause,), daemon=True)
        self._thread.start()

    def end(self):
        if not self.enabled or not self._active:
            return
        self._thread.join()
        self._active = False
        try:
            self._set(0)
            self._log('release')
        except AdalmError as e:
            self.failed = True
            print(f'[software_veto] ERROR: release failed ({e}); veto may be stuck high.')
            self._log('release-failed')

    def raise_if_failed(self):
        if self.failed:
            raise AdalmError('software veto release failed; veto may be stuck high')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Set the software veto line manually (1: veto, 0: release).')
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
