#!/usr/bin/env python3

"""What the DAQ is doing right now, published as small JSON files under
$MADAHOME/run for other processes (the LV-reset monitor, which appends its
records to the period's warning log, and the DAQ client):

  mada_run.json       where the DAQ is writing (period directory, file number, ...)
  mada_progress.json  events stored per board in the file being acquired
  mada_last_exit.json why the last DAQ run ended
  mada_stop_request.json  soft stop asked for by the DAQ client (read by the DAQ)
"""

import json
import os
import time

import psutil

from mada_daemon import run_name
from mada_process import program_name

MADAHOME = os.environ['MADAHOME']
STATE_PATH = MADAHOME + '/run/mada_run.json'
PROGRESS_PATH = MADAHOME + '/run/mada_progress.json'
LAST_EXIT_PATH = MADAHOME + '/run/mada_last_exit.json'
STOP_REQUEST_PATH = MADAHOME + '/run/mada_stop_request.json'

_context = {'period': None}  # period the DAQ is in, for the exit record


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _remove(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def set_period(period):
    """Note the period the DAQ is in (recorded in the exit record)."""
    _context['period'] = period


def publish_run_state(period_dir, file_id, **extra):
    """extra: run, period, valid_files, file_num, event_num, sci, boards and
    file_started_at [s], kept in the file for the DAQ client."""
    state = {'pid': os.getpid(), 'period_dir': os.path.abspath(period_dir), 'file_id': file_id}
    state.update(extra)
    if 'period' in extra:
        set_period(extra['period'])
    write_json(STATE_PATH, state)


def publish_progress(period_dir, file_id, event_num, counts, lagging):
    """Never raises: a failure here must not stop the DAQ."""
    progress = {'pid': os.getpid(), 'period_dir': os.path.abspath(period_dir), 'file_id': file_id,
                'time': time.time(), 'event_num': event_num, 'counts': dict(counts), 'lagging': list(lagging)}
    try:
        write_json(PROGRESS_PATH, progress)
    except OSError as e:
        print(f'WARNING: could not write {PROGRESS_PATH} ({e})')


def clear_progress():
    _remove(PROGRESS_PATH)


def clear_run_state():
    _remove(STATE_PATH)
    clear_progress()


def clear_stop_request():
    _remove(STOP_REQUEST_PATH)


def soft_stop_requested():
    """True when the client asked this DAQ to stop after the current file."""
    try:
        with open(STOP_REQUEST_PATH) as f:
            request = json.load(f)
    except (OSError, ValueError):
        return False
    return request.get('pid') == os.getpid() and request.get('mode') == 'soft'


def clear_last_exit():
    _remove(LAST_EXIT_PATH)


def write_last_exit(reason, message=None):
    """reason: 'stopped' (Ctrl+C, SIGTERM) or 'error'. Never raises."""
    record = {'reason': reason, 'message': message, 'time': time.time(),
              'run': run_name(), 'period': _context['period']}
    try:
        write_json(LAST_EXIT_PATH, record)
    except OSError as e:
        print(f'WARNING: could not write {LAST_EXIT_PATH} ({e})')


def read_run_state():
    """The published state, or None when no DAQ is running: a state left by a
    DAQ that died without clearing it is ignored."""
    try:
        with open(STATE_PATH, 'r') as f:
            state = json.load(f)
        proc = psutil.Process(state['pid'])
        if program_name(proc.cmdline()) != 'mada.py':
            return None
        return state
    except (OSError, ValueError, KeyError, psutil.Error):
        return None
