#!/usr/bin/env python3

import os
import signal

from mada_daemon import PIDFILE_PATH


def is_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def remove_stale_pidfile():
    try:
        os.remove(PIDFILE_PATH)
    except FileNotFoundError:
        pass


def run_stop_daq():
    try:
        with open(PIDFILE_PATH, 'r') as f:
            text = f.read().strip()
    except FileNotFoundError:
        print(f'No pidfile at {PIDFILE_PATH}. Is mada.py --daemon running?')
        return

    if not text.isdigit():
        print(f'{PIDFILE_PATH} does not contain a PID ({text!r}). Removing it.')
        remove_stale_pidfile()
        return

    pid = int(text)
    if not is_alive(pid):
        print(f'PID {pid} from {PIDFILE_PATH} is not running (stale pidfile). Removing it.')
        remove_stale_pidfile()
        return

    print(f'Sending SIGTERM to PID {pid}...')
    try:
        os.kill(pid, signal.SIGTERM)
    except PermissionError:
        print(f'No permission to signal PID {pid}.')


def main():
    run_stop_daq()


if __name__ == '__main__':
    main()
