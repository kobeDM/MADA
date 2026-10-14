#!/usr/bin/env python3

"""Per-run bookkeeping: the perNNNN directories, the .mada/.info file names,
the .info files (start and end of each file) and the rate log."""

import glob
import json
import os

from mada_config import load_config, board_entry_by_ip
from mada_rate_log import write_rate_log, RATE_ROOT


def _period_dir(period_id):
    return 'per' + str(period_id).zfill(4)


class RunLogger:
    def __init__(self, config_path, period_id):
        self.config_path = config_path
        self.period_id = period_id

    @staticmethod
    def new_period() -> int:
        period = 0
        while os.path.exists(_period_dir(period)):
            period += 1
        os.makedirs(_period_dir(period))
        return period

    @classmethod
    def latest(cls, config_path):
        """RunLogger of the newest perNNNN directory, or None if there is none."""
        period = -1
        while os.path.exists(_period_dir(period + 1)):
            period += 1
        return cls(config_path, period) if period >= 0 else None

    def latest_file_id(self):
        """Highest file number that has an .info file in this period, or -1."""
        file_id = -1
        while glob.glob(f'{_period_dir(self.period_id)}/*_{str(file_id + 1).zfill(4)}.info'):
            file_id += 1
        return file_id

    def _base(self, file_id, board_id):
        return f'{_period_dir(self.period_id)}/{board_id}_{str(file_id).zfill(4)}'

    def mada_file_paths(self, file_id, boards):
        return {board_id: self._base(file_id, board_id) + '.mada' for board_id, ip in boards}

    def write_info_start(self, file_id, boards, start_time):
        config_load = load_config(self.config_path)

        for board_id, ip in boards:
            entry = board_entry_by_ip(config_load, ip)
            if entry is None:
                print(f'WARNING: no config entry for {board_id} (IP {ip}); its .info file is not written')
                continue

            info = {'gigaIwaki': dict(entry), 'runinfo': {'start': start_time}}
            with open(self._base(file_id, board_id) + '.info', 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=4)

    def finalize_file(self, file_id, boards, end_time, start_time=None):
        """Write end time and size into each board's .info (unless it already
        has an end) and append the rate log. start_time defaults to the one in
        the .info files. Returns the sizes in board order."""
        sizes = []
        for board_id, ip in boards:
            base = self._base(file_id, board_id)
            mada_missing = not os.path.exists(base + '.mada')
            size = 0 if mada_missing else os.path.getsize(base + '.mada')
            sizes.append(size)
            if mada_missing:
                print(f'WARNING: {base}.mada not found (connection failure suspected on {board_id})')
            print('size= ', size, 'byte')

            start_time = self._update_info_end(base + '.info', end_time, size, mada_missing, start_time)

        if start_time is not None:
            self._write_rate_log(start_time, end_time, sizes)
        return sizes

    @staticmethod
    def _update_info_end(info_path, end_time, size, mada_missing, start_time):
        """Returns start_time, filled from this .info when it was None."""
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                info = json.load(f)
        except FileNotFoundError:
            print(f'WARNING: {info_path} not found; not updated')
            return start_time
        except ValueError as e:
            print(f'WARNING: {info_path} is not valid JSON ({e}); not updated')
            return start_time

        runinfo = info.setdefault('runinfo', {})
        if start_time is None:
            start_time = runinfo.get('start')
        if 'end' in runinfo:
            return start_time

        runinfo.update({'end': end_time, 'size': str(size)})
        if mada_missing:
            runinfo['error'] = 'mada file not found (connection failure suspected)'

        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=4)
        return start_time

    @staticmethod
    def _write_rate_log(start_time, end_time, sizes):
        try:
            write_rate_log(RATE_ROOT, start_time, end_time, sizes)
        except OSError as e:
            print(f'WARNING: could not write the rate log ({e})')
