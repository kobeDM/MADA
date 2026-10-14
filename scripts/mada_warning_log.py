#!/usr/bin/env python3

"""The warning log of a period (perNNNN/warnings.log), written by the DAQ and
by the LV-reset monitor in the same format. One line per record, tab
separated: epoch s, ISO time, file number, source (a board, DAQ or LV),
message. Messages from the tools use `LEVEL t=<epoch s> kind=<kind> key=value`."""

import datetime
import threading
import time

WARNING_LOG_NAME = 'warnings.log'

_lock = threading.Lock()


def event_message(level, kind, **fields):
    parts = [level, f't={time.time():.3f}', f'kind={kind}']
    parts += [f'{key}={value}' for key, value in fields.items()]
    return ' '.join(parts)


def append_warning(path, file_id, source, message):
    """Append one record. Never raises: a log failure must not stop the DAQ or
    the monitor."""
    now = time.time()
    stamp = datetime.datetime.fromtimestamp(now).isoformat(timespec='milliseconds')
    message = message.replace('\t', ' ').replace('\n', ' ')
    line = '\t'.join([f'{now:.3f}', stamp, str(file_id).zfill(4), source, message]) + '\n'
    try:
        with _lock, open(path, 'a', encoding='utf-8') as f:
            f.write(line)
    except OSError as e:
        print(f'WARNING: could not write {path} ({e})')
