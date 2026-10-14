#!/usr/bin/env python3

"""Find and stop MADA processes by program name. A process matches when the
program it runs (the binary, or the script a Python interpreter runs) has
exactly the given name, so a shell or editor that merely mentions the name
in its command line is left alone."""

import os

import psutil

TERM_TIMEOUT = 3.0  # sec to wait after SIGTERM before SIGKILL
KILL_TIMEOUT = 3.0  # sec to wait after SIGKILL


def program_name(cmdline):
    """Name of the program a command line runs, or None for an empty one."""
    if not cmdline:
        return None

    first = os.path.basename(cmdline[0])
    if first.startswith('python'):
        for arg in cmdline[1:]:
            if not arg.startswith('-'):
                return os.path.basename(arg)
    return first


def _matches(prog, names):
    return prog is not None and any(prog == name or prog == name + '.py' for name in names)


def find_processes(names):
    """Running processes (other than this one) whose program is one of names."""
    found = []
    for proc in psutil.process_iter(['pid', 'cmdline']):
        if proc.info['pid'] == os.getpid():
            continue
        if _matches(program_name(proc.info['cmdline']), names):
            found.append(proc)
    return found


def stop_processes(names, label='processes'):
    """SIGTERM every matching process, SIGKILL the ones that stay. Returns the
    set of PIDs that were stopped."""
    procs = find_processes(names)
    if not procs:
        print(f'No {label} found to kill.')
        return set()

    stopped = set()
    live = []
    for proc in procs:
        try:
            print(f"Killing PID {proc.pid}: {' '.join(proc.info['cmdline'] or [])}")
            proc.terminate()
            live.append(proc)
        except psutil.NoSuchProcess:
            stopped.add(proc.pid)
        except psutil.AccessDenied:
            print(f'WARNING: no permission to stop PID {proc.pid}')

    gone, alive = psutil.wait_procs(live, timeout=TERM_TIMEOUT)
    stopped.update(p.pid for p in gone)

    for proc in alive:
        try:
            print(f'PID {proc.pid} ignored SIGTERM; sending SIGKILL')
            proc.kill()
        except psutil.NoSuchProcess:
            pass

    gone, alive = psutil.wait_procs(alive, timeout=KILL_TIMEOUT)
    stopped.update(p.pid for p in gone)
    for proc in alive:
        print(f'WARNING: PID {proc.pid} did not stop')

    return stopped
