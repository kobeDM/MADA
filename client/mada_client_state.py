"""The DAQ state as seen from the files and processes: phase, status, progress.
Nothing is kept in memory except the client's own record of what it started
and stopped, which is stored in run/mada_client.json."""

import json
import time

import psutil

import mada_client_paths as paths
import mada_autoreset_ctl
import mada_daemon
import mada_run_state
from mada_client_files import latest_run
from mada_process import find_processes, program_name

BLOCKING_PROGRAMS = ('mada_scan', 'mada_calib', 'MadaIwaki')
STALE_SEC = 5.0  # sec without a progress update
DAQ_PROGRAM = 'mada.py'


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_record():
    return read_json(paths.CLIENT_STATE_PATH) or {}


def save_record(record):
    mada_run_state.write_json(paths.CLIENT_STATE_PATH, record)


def is_daq_process(pid):
    try:
        proc = psutil.Process(pid)
        return (proc.status() != psutil.STATUS_ZOMBIE
                and program_name(proc.cmdline()) == DAQ_PROGRAM)
    except psutil.Error:
        return False


def daemon_pid():
    """PID of the running DAQ: the daemon pidfile, else the PID in the run state
    (a mada.py started from a terminal)."""
    try:
        with open(mada_daemon.PIDFILE_PATH) as f:
            pid = int(f.read().strip())
        if is_daq_process(pid):
            return pid
    except (OSError, ValueError):
        pass
    state = mada_run_state.read_run_state()
    return state['pid'] if state else None


def current_phase():
    """(phase, pid, run state of that pid or None)."""
    pid = daemon_pid()
    if pid is None:
        return 'idle', None, None
    state = mada_run_state.read_run_state()
    state = state if state and state.get('pid') == pid else None
    stop = load_record().get('stop')
    if stop and stop.get('pid') == pid:
        return 'stopping', pid, state
    return ('running' if state else 'starting'), pid, state


def blocked_by():
    procs = find_processes(BLOCKING_PROGRAMS)
    return program_name(procs[0].cmdline()) if procs else None


def _daq_info(pid, state, record):
    start = record.get('start') if (record.get('start') or {}).get('pid') == pid else None
    stop = record.get('stop') if (record.get('stop') or {}).get('pid') == pid else None
    info = {'pid': pid, 'run': None, 'period': None, 'file_id': None, 'valid_files': None,
            'file_num': None, 'event_num': None, 'sci': None, 'started_at': None,
            'file_started_at': None, 'stop_requested_at': stop['at'] if stop else None,
            'stop_mode': stop.get('mode', 'force') if stop else None,
            'boards': []}
    if start:
        info.update({k: start[k] for k in ('run', 'file_num', 'event_num', 'sci')})
        info['started_at'] = start['started_at']
    if state:
        info.update({k: state[k] for k in info if k in state and k not in ('pid', 'stop_requested_at', 'stop_mode')})
    return info


def _last_exit(record):
    """The record of how the last DAQ run ended; 'crashed' when a run the client
    started is gone without leaving one."""
    exit_record = read_json(mada_run_state.LAST_EXIT_PATH)
    start = record.get('start')
    if exit_record and (not start or exit_record['time'] >= start['started_at']):
        return exit_record
    if start:
        crash = record.get('crash')
        if not crash or crash.get('pid') != start['pid']:
            crash = {'reason': 'crashed', 'message': None, 'time': time.time(),
                     'run': start['run'], 'period': None, 'pid': start['pid']}
            record['crash'] = crash
            save_record(record)
        return {k: v for k, v in crash.items() if k != 'pid'}
    return None


def _scaler_state(daq_running):
    """The scaler as recorded by mada.py (None when it never used one). A scaler
    recorded as running while no DAQ runs is 'orphaned'."""
    record = read_json(paths.SCALER_STATE_PATH)
    if not record:
        return None
    state = record.get('state')
    if state == 'running' and not daq_running:
        state = 'orphaned'
    return {'state': state, 'period': record.get('period'), 'time': record.get('time')}


def build_status(settings):
    phase, pid, state = current_phase()
    record = load_record()
    veto = read_json(paths.VETO_STATE_PATH) or {}
    monitor_up = settings.simulate or mada_autoreset_ctl.monitor_pid() is not None
    return {
        'api_version': 1,
        'time': time.time(),
        'phase': phase,
        'blocked_by': blocked_by() if phase == 'idle' else None,
        'latest_run': latest_run(settings),
        'daq': _daq_info(pid, state, record) if pid else None,
        'monitor': {'autoreset_running': monitor_up,
                    'veto': {'failed': bool(veto.get('failed', False)),
                             'asserted': bool(veto.get('asserted', False))},
                    'scaler': _scaler_state(pid is not None)},
        'last_exit': None if pid else _last_exit(record),
    }


def build_progress():
    now = time.time()
    empty = {'time': now, 'stale': False, 'file_id': None, 'event_num': None, 'boards': {}, 'lagging': []}
    phase, pid, _ = current_phase()
    stop = load_record().get('stop') or {}
    soft_pending = phase == 'stopping' and stop.get('pid') == pid and stop.get('mode') == 'soft'
    progress = read_json(mada_run_state.PROGRESS_PATH)
    if (phase != 'running' and not soft_pending) or not progress or progress.get('pid') != pid:
        return empty
    return {'time': progress['time'], 'stale': now - progress['time'] > STALE_SEC,
            'file_id': progress['file_id'], 'event_num': progress['event_num'],
            'boards': {b: {'events': n} for b, n in progress['counts'].items()},
            'lagging': progress['lagging']}
