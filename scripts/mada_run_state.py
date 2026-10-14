#!/usr/bin/env python3

"""Where the DAQ is writing right now (period directory and file number),
published for the LV-reset monitor, which runs as a separate process and
appends its records to that period's warning log."""

import json
import os

import psutil

from mada_process import program_name

MADAHOME = os.environ['MADAHOME']
STATE_PATH = MADAHOME + '/run/mada_run.json'


def publish_run_state(period_dir, file_id):
    state = {'pid': os.getpid(), 'period_dir': os.path.abspath(period_dir), 'file_id': file_id}
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f)
    os.replace(tmp, STATE_PATH)


def clear_run_state():
    try:
        os.remove(STATE_PATH)
    except FileNotFoundError:
        pass


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
