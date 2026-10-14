#!/usr/bin/env python3

"""Start/lookup helpers for the always-on regulator autoreset monitor
(mada_regulator_autoreset.py). Kept separate so that low-level tools such as
mada_set_ap.py can ensure the monitor is running without import cycles."""

import os
import sys
import time
import fcntl
import signal
import subprocess

MADAHOME = os.environ['MADAHOME']
RUN_DIR = MADAHOME + '/run'

SCRIPT = MADAHOME + '/scripts/mada_regulator_autoreset.py'
PIDFILE_PATH = RUN_DIR + '/mada_autoreset.pid'
CONFIG_RECORD_PATH = RUN_DIR + '/mada_autoreset.config'
LOCK_PATH = RUN_DIR + '/mada_autoreset.lock'
LOG_PATH = RUN_DIR + '/mada_autoreset.log'

START_TIMEOUT = 15.0  # sec
STOP_TIMEOUT = 30.0   # sec


class MonitorError(RuntimeError):
    """Raised when the autoreset monitor is required but cannot be started."""


def _read(path):
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except OSError:
        return None


def monitor_pid():
    """PID of the running monitor, or None. Guards against a stale pidfile
    whose PID was reused by an unrelated process."""
    text = _read(PIDFILE_PATH)
    if not text or not text.isdigit():
        return None

    pid = int(text)
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            cmdline = f.read().decode(errors='replace')
    except OSError:
        return None
    return pid if 'mada_regulator_autoreset' in cmdline else None


def recorded_config():
    return _read(CONFIG_RECORD_PATH)


def acquire_lock(wait=0.0):
    """Exclusive instance lock held for the monitor's whole lifetime. Returns
    the open file object (keep it referenced), or None if another monitor
    holds it."""
    os.makedirs(RUN_DIR, exist_ok=True)
    f = open(LOCK_PATH, 'w')
    deadline = time.time() + wait
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except OSError:
            if time.time() >= deadline:
                f.close()
                return None
            time.sleep(0.2)


def _wait_until(predicate, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.3)
    return predicate()


def ensure_autoreset_running(config_path, timeout=START_TIMEOUT):
    """Make sure a monitor for config_path is running; start (or restart, if it
    was started with another config) it when needed. Returns True on success."""
    config_path = os.path.abspath(config_path)

    pid = monitor_pid()
    if pid and recorded_config() == config_path:
        return True

    if pid:
        print(f'[autoreset] Restarting the monitor with {config_path} (was {recorded_config()}).')
        os.kill(pid, signal.SIGTERM)
        if not _wait_until(lambda: monitor_pid() is None, STOP_TIMEOUT):
            print('[autoreset] ERROR: the running monitor did not stop.')
            return False
    else:
        print('[autoreset] Starting the regulator autoreset monitor...')

    subprocess.run([sys.executable, SCRIPT, '-d', '-c', config_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if _wait_until(lambda: monitor_pid() is not None and recorded_config() == config_path, timeout):
        return True

    print(f'[autoreset] ERROR: the monitor did not start (see {LOG_PATH}).')
    return False
