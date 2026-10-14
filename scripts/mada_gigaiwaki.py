#!/usr/bin/env python3

"""The MadaIwaki readers, one process per board: start them (restarting the
ones that fail to come up), and stop them."""

import os
import subprocess
import threading
import time

from mada_errors import MadaError

MADAHOME = os.environ['MADAHOME']
MADA_IWAKI = MADAHOME + '/bin/MadaIwaki'

START_ATTEMPTS = 3  # tries to bring one reader up before giving up
SETTLE_TIME = 1.0   # sec a new reader must stay alive to count as connected


class GigaIwakiError(MadaError):
    """Raised when a reader exits with a non-zero status (e.g. it lost the
    connection to its board), so the caller can stop the DAQ instead of
    treating the exit as a normal 'file complete' event."""


def _forward_stderr(board_id, pipe, warn):
    for line in pipe:
        line = line.rstrip()
        if line:
            print(f'[{board_id}] {line}', flush=True)
            if warn:
                warn(board_id, line)


def start_reader(board_id, ip, event_num, mada_file, warn=None):
    cmd = [MADA_IWAKI, '-n', str(event_num), '-f', mada_file, '-i', ip]
    # stdout carries a per-event progress line (up to event_num times per
    # file) that would bloat the log, so it is discarded; stderr carries only
    # diagnostics (errors, and the stall/slow-write warnings of MadaIwaki) and
    # is forwarded, tagged with the board, to our own stdout and to warn(),
    # which keeps it in the period's warning log.
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    threading.Thread(target=_forward_stderr, args=(board_id, proc.stderr, warn), daemon=True).start()
    return proc


def _failed(proc):
    return proc.poll() is not None and proc.returncode != 0


def start_readers(event_num, boards, mada_files, warn=None, attempts=START_ATTEMPTS, settle=SETTLE_TIME):
    """Start one reader per board and return once all of them have stayed
    alive for `settle` seconds. A reader that dies while coming up (typically a
    refused or dropped TCP connection) is restarted on its own, which is safe
    because nothing is acquired yet: the caller sends DAQ enable and counter
    reset to all boards together only after this returns. Raises
    GigaIwakiError, with every reader stopped, if a board still fails."""
    ips = dict(boards)
    procs = {board_id: start_reader(board_id, ip, event_num, mada_files[board_id], warn) for board_id, ip in boards}

    for attempt in range(1, attempts + 1):
        time.sleep(settle)
        failed = [board_id for board_id, proc in procs.items() if _failed(proc)]
        if not failed:
            return procs

        if attempt == attempts:
            break
        for board_id in failed:
            message = (f'reader exited (code {procs[board_id].returncode}) while starting; '
                       f'restarting ({attempt}/{attempts - 1})')
            print(f'WARNING: {board_id}: {message}')
            if warn:
                warn(board_id, 'WARNING ' + message)
            procs[board_id] = start_reader(board_id, ips[board_id], event_num, mada_files[board_id], warn)

    kill_readers(procs)
    raise GigaIwakiError(f'reader for {", ".join(failed)} could not be started after {attempts} attempts')


def kill_readers(procs):
    for board_id, proc in procs.items():
        if proc.poll() is None:
            proc.kill()
            print(f'Killed process for {board_id} (PID: {proc.pid})')
        proc.wait()
