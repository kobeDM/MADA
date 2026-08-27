#!/usr/bin/env python3

import os
import signal

from mada_daemon import PIDFILE_PATH


def is_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def run_stop_daq():
    if not os.path.exists(PIDFILE_PATH):
        print(f'No pidfile at {PIDFILE_PATH}. Is mada.py --daemon running?')
        return

    with open(PIDFILE_PATH, 'r') as f:
        pid = int(f.read().strip())

    if not is_alive(pid):
        print(f'PID {pid} from {PIDFILE_PATH} is not running (stale pidfile). Removing it.')
        os.remove(PIDFILE_PATH)
        return

    print(f'Sending SIGTERM to PID {pid}...')
    os.kill(pid, signal.SIGTERM)


def main():
    run_stop_daq()


if __name__ == '__main__':
    main()
