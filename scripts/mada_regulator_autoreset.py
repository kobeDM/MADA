#!/usr/bin/env python3

import os
import sys
import time
import signal
import argparse

from mada_ap_state import get_ap_state
from mada_regulator_monitor import RegulatorAutoresetMonitor
from mada_software_veto import SoftwareVeto
from mada_daemon import detach
from mada_autoreset_ctl import (PIDFILE_PATH, CONFIG_RECORD_PATH, LOG_PATH,
                                monitor_pid, acquire_lock)

CONFIG = './MADA_config.json'
IDLE_EXIT_DEFAULT = 600.0  # sec, exit after all boards had AP off for this long
IDLE_CHECK_INTERVAL = 30.0  # sec

def arg_parser():
    parser = argparse.ArgumentParser(description='Watch MPOD over-current logs and reset the regulator (AP 0->1) on any board mapped to the module that reports a new over-limit line, driving the software veto meanwhile. Run it once and keep it running, independently of mada.py.')
    parser.add_argument('-c', '--config', default=CONFIG)
    parser.add_argument('-d', '--daemon', action='store_true', help='Run in the background (log: run/mada_autoreset.log)')
    parser.add_argument('--stop', action='store_true', help='Stop the running background monitor')
    parser.add_argument('--idle-exit', type=float, default=IDLE_EXIT_DEFAULT, help='Exit after every active board has had AP off for this many seconds (0: never; default 600)')
    args = parser.parse_args()
    return args

def stop_daemon():
    pid = monitor_pid()
    if pid is None:
        print('No running autoreset monitor found.')
        return
    print(f'Sending SIGTERM to PID {pid}...')
    os.kill(pid, signal.SIGTERM)


def all_boards_ap_off(boards):
    return all(get_ap_state(ip) is False for ip in boards)


def main():
    args = arg_parser()

    if args.stop:
        stop_daemon()
        return

    if monitor_pid() is not None:
        print('An autoreset monitor is already running.')
        sys.exit(1)

    config_path = os.path.abspath(args.config)
    if not os.path.isfile(config_path):
        print(f'Error: config file {config_path} not found.')
        sys.exit(1)

    if args.daemon:
        detach(LOG_PATH)

    lock = acquire_lock(wait=5.0)
    if lock is None:
        print('Another autoreset monitor holds the lock; exiting.')
        sys.exit(0)

    with open(PIDFILE_PATH, 'w') as f:
        f.write(str(os.getpid()))
    with open(CONFIG_RECORD_PATH, 'w') as f:
        f.write(config_path)

    def _handle_sigterm(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_sigterm)

    print('*** mada_regulator_autoreset.py start ***')
    veto = SoftwareVeto(config_path)
    veto.initialize()
    monitor = RegulatorAutoresetMonitor(config_path, veto=veto)
    monitor.start()

    boards = [ip for boards_ in monitor.module_boards.values() for _, ip in boards_]
    off_since = None
    try:
        while True:
            time.sleep(IDLE_CHECK_INTERVAL)
            if args.idle_exit <= 0 or not boards:
                continue
            if all_boards_ap_off(boards):
                off_since = off_since or time.time()
                if time.time() - off_since >= args.idle_exit:
                    print(f'All boards have had AP off for {args.idle_exit:.0f} s; exiting.')
                    break
            else:
                off_since = None
    except KeyboardInterrupt:
        print('Stopping monitor...')
    finally:
        monitor.stop()
        veto.shutdown()
        for path in (PIDFILE_PATH, CONFIG_RECORD_PATH):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    print('*** mada_regulator_autoreset.py end ***')

if __name__ == '__main__':
    main()
