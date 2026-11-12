"""Starting and stopping the DAQ: mada.py -d is run in the run directory, and
stopped with SIGTERM (the same shutdown as Ctrl+C)."""

import datetime
import os
import shutil
import signal
import subprocess
import sys
import threading
import time

import mada_client_paths as paths
import mada_client_files as files
import mada_client_state as state
from mada_client_config import RUN_PATTERN
from mada_client_errors import ApiError

START_TIMEOUT = 30.0  # sec for mada.py -d to check the config and detach
PID_WAIT = 5.0        # sec for the daemon pidfile to appear
CONFIG_NAME = 'MADA_config.json'

_lock = threading.Lock()


def log_operation(remote, action, params, result):
    stamp = datetime.datetime.now().isoformat(timespec='seconds')
    line = f'{stamp}\t{remote}\t{action}\t{params}\t{result}\n'
    try:
        os.makedirs(paths.RUN_DIR, exist_ok=True)
        with open(paths.CLIENT_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line)
    except OSError:
        pass


def _check_numbers(settings, file_num, event_num):
    if not 1 <= file_num <= settings.file_num_max:
        raise ApiError(422, 'invalid_request', f'file_num must be 1-{settings.file_num_max}')
    if not 1 <= event_num <= settings.event_num_max:
        raise ApiError(422, 'invalid_request', f'event_num must be 1-{settings.event_num_max}')


def _prepare_run_dir(settings, run, config_from):
    """Create the run directory if needed and make sure it has a config
    (copied from another run for a new run). Returns the directory."""
    run_dir = os.path.join(settings.data_root, run)
    config = f'{run_dir}/{CONFIG_NAME}'
    if os.path.isfile(config):
        if config_from:
            raise ApiError(422, 'invalid_request', f'run {run} already has a config; config_from is not allowed')
        return run_dir

    source = config_from or (files.latest_run(settings) if settings.carry_over_config else None)
    if not source:
        raise ApiError(422, 'config_not_found', f'run {run} has no {CONFIG_NAME} and there is nothing to copy it from')
    source_config = f'{files.run_path(settings, source)}/{CONFIG_NAME}'
    if not os.path.isfile(source_config):
        raise ApiError(422, 'config_not_found', f'run {source} has no {CONFIG_NAME}')
    os.makedirs(run_dir, exist_ok=True)
    shutil.copy2(source_config, config)
    return run_dir


def _run_mada(settings, run_dir, file_num, event_num, sci):
    cmd = [sys.executable, paths.MADA_PY, '-d', '-c', CONFIG_NAME, '-f', str(file_num), '-n', str(event_num)]
    if sci:
        cmd.append('--sci')
    env = dict(os.environ, MADAHOME=paths.MADAHOME, **settings.sim_env)
    try:
        done = subprocess.run(cmd, cwd=run_dir, env=env, capture_output=True, text=True, timeout=START_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise ApiError(503, 'start_failed', f'mada.py did not detach within {START_TIMEOUT:.0f} s')
    if done.returncode != 0:
        output = (done.stdout + done.stderr).strip()
        raise ApiError(422, 'config_invalid', output[-2000:] or f'mada.py exited with code {done.returncode}')


def _wait_for_pid():
    deadline = time.time() + PID_WAIT
    while time.time() < deadline:
        pid = state.daemon_pid()
        if pid:
            return pid
        time.sleep(0.1)
    raise ApiError(503, 'start_failed', 'the DAQ daemon did not come up')


def start_daq(settings, request, remote):
    """Start the DAQ; returns the new phase. request: run, file_num, event_num, sci, config_from."""
    params = dict(request)
    try:
        with _lock:
            phase = state.current_phase()[0]
            busy = state.blocked_by() if phase == 'idle' else None
            if phase != 'idle' or busy:
                raise ApiError(409, 'busy', f'{busy} is running' if busy else f'the DAQ is {phase}')

            run = request.get('run') or files.latest_run(settings)
            if not run or not RUN_PATTERN.match(run):
                raise ApiError(422, 'invalid_request', f'invalid run name {run!r}')
            file_num = request.get('file_num') or settings.file_num_default
            event_num = request.get('event_num') or settings.event_num_default
            _check_numbers(settings, file_num, event_num)
            params.update(run=run, file_num=file_num, event_num=event_num)

            run_dir = _prepare_run_dir(settings, run, request.get('config_from'))
            started_at = time.time()
            _run_mada(settings, run_dir, file_num, event_num, bool(request.get('sci')))
            pid = _wait_for_pid()
            record = {'start': {'pid': pid, 'run': run, 'file_num': file_num, 'event_num': event_num,
                                'sci': bool(request.get('sci')), 'started_at': started_at}}
            state.save_record(record)
            files.clear_cache()
    except ApiError as e:
        log_operation(remote, 'start', params, f'{e.status} {e.code}')
        raise
    log_operation(remote, 'start', params, 'ok')
    return 'starting'


def stop_daq(remote):
    """Send SIGTERM to the DAQ; returns the new phase."""
    with _lock:
        phase, pid, _ = state.current_phase()
        if pid is None:
            log_operation(remote, 'stop', {}, '409 not_running')
            raise ApiError(409, 'not_running', 'the DAQ is not running')
        if phase != 'stopping':
            record = state.load_record()
            record['stop'] = {'pid': pid, 'at': time.time()}
            state.save_record(record)
            os.kill(pid, signal.SIGTERM)
            log_operation(remote, 'stop', {'pid': pid}, 'ok')
    return 'stopping'
