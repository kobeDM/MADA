#!/usr/bin/env python3

import os
import signal
import sys

MADAHOME = os.environ['MADAHOME']
RUN_DIR = MADAHOME + '/run'
PIDFILE_PATH = RUN_DIR + '/mada_daemon.pid'


def run_name():
    """Name of the launch directory (e.g. a date-named data directory such
    as 20260817), used to namespace log files by run."""
    return os.path.basename(os.getcwd())


def log_path(period):
    """One log file per period: period numbers only increase within a run
    directory (RunLogger.new_period() never reuses one), so this name is
    unique even across repeated same-day runs."""
    return f'{RUN_DIR}/{run_name()}_{str(period).zfill(4)}.log'


def install_sigterm_handler():
    """Make SIGTERM raise KeyboardInterrupt, so `kill <PID>` runs the same
    shutdown path (regulator/power teardown) as Ctrl+C."""
    def _handle_sigterm(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _handle_sigterm)


def write_pidfile(pid):
    with open(PIDFILE_PATH, 'w') as f:
        f.write(str(pid))


def remove_pidfile():
    try:
        os.remove(PIDFILE_PATH)
    except FileNotFoundError:
        pass


def _redirect_stdio(log_file):
    sys.stdout.flush()
    sys.stderr.flush()

    log_fd = os.open(log_file, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o644)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())
    os.close(log_fd)

    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)


def switch_log(period):
    """Point stdout/stderr at the log file for a new period. Call this
    after crossing into a new period while daemonized."""
    os.makedirs(RUN_DIR, exist_ok=True)
    _redirect_stdio(log_path(period))


def daemonize(first_period):
    """Detach the current process from the controlling terminal and
    redirect stdout/stderr to first_period's log file. The parent process
    exits after writing PIDFILE_PATH, which mada_stop_daq.py uses to
    signal the child."""
    os.makedirs(RUN_DIR, exist_ok=True)
    log_file = log_path(first_period)

    pid = os.fork()
    if pid > 0:
        write_pidfile(pid)
        print(f'Started DAQ in background (PID {pid}). Log: {log_file}')
        os._exit(0)

    # No os.chdir('/') here: mada.py resolves perNNNN/ and the config path
    # relative to the launch directory, so the working directory must stay.
    os.setsid()

    devnull_fd = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull_fd, sys.stdin.fileno())
    os.close(devnull_fd)

    _redirect_stdio(log_file)
