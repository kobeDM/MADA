#!/usr/bin/env python3

"""Which operations the DAQ accepts right now. One place for the rules, used
both for the buttons on the dashboard (via ServerState.snapshot) and for the
checks made just before a request is sent to daq-client.

A force stop is SIGTERM to mada.py, which acts like Ctrl+C. It is only safe
while a file is being acquired: while the readers are started, the counters
are reset and DAQ enable is raised (ADALM control), or while DAQ enable is
lowered and the readers are stopped at the end of a file, an interrupt can
leave the boards in a bad state. mada.py marks the first window with
daq.file_started_at == null and clears the progress file in the second."""

REASON_NOT_RUNNING = 'not_running'
REASON_BUSY = 'busy_file_update'


def start_refusal(status):
    """None if a DAQ can be started, else (code, message)."""
    if status is None:
        return 'unknown', 'The DAQ state is unknown (no connection to daq-client)'
    if status.get('phase') != 'idle':
        return 'busy', f"The DAQ is {status.get('phase')}"
    if status.get('blocked_by'):
        return 'busy', f"{status['blocked_by']} is running"
    return None


def soft_stop_refusal(status):
    """A soft stop only leaves a request for mada.py, so it is accepted at any
    point of a running DAQ (once)."""
    if status is None:
        return 'unknown', 'The DAQ state is unknown (no connection to daq-client)'
    if status.get('phase') != 'running':
        return REASON_NOT_RUNNING, f"The DAQ is {status.get('phase')}, not running"
    return None


def force_stop_refusal(status, progress):
    """None if SIGTERM is safe now, else (code, message)."""
    if status is None:
        return 'unknown', 'The DAQ state is unknown (no connection to daq-client)'
    phase = status.get('phase')
    daq = status.get('daq') or {}
    soft_pending = phase == 'stopping' and daq.get('stop_mode') == 'soft'
    if phase != 'running' and not soft_pending:
        return REASON_NOT_RUNNING, f'The DAQ is {phase}, not running'

    if daq.get('file_started_at') is None:
        return REASON_BUSY, 'A file is being set up (readers, counter reset, DAQ enable); try again in a moment'

    progress = progress or {}
    boards = progress.get('boards') or {}
    if progress.get('file_id') is None or not boards:
        return REASON_BUSY, 'The file is being finished or the progress is not available yet; try again in a moment'
    if daq.get('file_id') is not None and progress.get('file_id') != daq.get('file_id'):
        return REASON_BUSY, 'The file has just changed; try again in a moment'
    event_num = progress.get('event_num')
    if event_num and all(b.get('events', 0) >= event_num for b in boards.values()):
        return REASON_BUSY, 'The file is complete and is being closed (DAQ enable is lowered); try again in a moment'
    return None


def controls(status, progress):
    """What the dashboard enables: {key: {'enabled': bool, 'reason': str|None}}."""
    def entry(refusal):
        return {'enabled': refusal is None, 'reason': refusal[1] if refusal else None}

    return {
        'start': entry(start_refusal(status)),
        'soft_stop': entry(soft_stop_refusal(status)),
        'force_stop': entry(force_stop_refusal(status, progress)),
    }
