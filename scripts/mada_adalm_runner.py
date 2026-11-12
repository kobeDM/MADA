#!/usr/bin/env python3

"""Run bin/AdalmControl for one ADALM role. All callers (threads and
processes) are serialized with a file lock, because two processes opening the
same ADALM at once make it appear busy or missing."""

import fcntl
import os
import subprocess
import time

from mada_errors import MadaError

MADAHOME = os.environ['MADAHOME']
ADALM_CTRL = MADAHOME + '/bin/AdalmControl'
LOCK_PATH = MADAHOME + '/run/adalm.lock'

LOCK_TIMEOUT = 60.0  # sec to wait for the lock before giving up
CALL_TIMEOUT = 20.0  # sec one AdalmControl call may take, plus the pulse width


class AdalmError(MadaError):
    """Raised when AdalmControl keeps failing after all retries."""


def _acquire_lock():
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    lock = open(LOCK_PATH, 'w')
    deadline = time.time() + LOCK_TIMEOUT
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock
        except OSError:
            if time.time() >= deadline:
                lock.close()
                raise AdalmError(f'could not get the ADALM lock within {LOCK_TIMEOUT:.0f} s (is AdalmControl hung?)')
            time.sleep(0.05)


def acquire_adalm_lock():
    """The lock all ADALM users take while they open an ADALM; the caller closes the returned file to release it."""
    return _acquire_lock()


def _run_once(cmd, timeout):
    try:
        return subprocess.run(cmd, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f'WARNING: AdalmControl did not finish within {timeout:.0f} s and was killed')
        return None


def run_adalm_control(serial, latch, width=None, retries=3, retry_wait=1.0, mask=None, analog=True):
    cmd = [ADALM_CTRL, '-s', serial, '-l', str(latch)]
    if mask is not None:
        cmd += ['-m', hex(mask)]
    if not analog:
        cmd.append('--no-analog')
    if width is not None:
        cmd += ['-w', str(width)]
    print('Execute: ' + ' '.join(cmd))

    timeout = CALL_TIMEOUT + (width or 0.0)
    lock = _acquire_lock()
    try:
        for attempt in range(1, retries + 1):
            ret = _run_once(cmd, timeout)
            if ret == 0:
                return
            if ret is not None:
                print(f'WARNING: AdalmControl failed (code {ret}), attempt {attempt}/{retries}')
            if attempt < retries:
                time.sleep(retry_wait)
    finally:
        lock.close()

    raise AdalmError(f'AdalmControl failed {retries} times for {serial} (latch={latch})')
