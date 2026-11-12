#!/usr/bin/env python3

"""Acquire the files of one period. One file is one cycle: with DAQ enable
low, start the readers, reset the counters, raise DAQ enable, wait until a
reader has stored its events, then lower DAQ enable again and close the file."""

import time

from mada_adalm_roles import ROLE_DAQ_ENABLE, ROLE_COUNTER_RESET
from mada_adalm_runner import run_adalm_control, AdalmError
from mada_autoreset_ctl import ensure_autoreset_running, MonitorError
from mada_errors import MadaError
from mada_gigaiwaki import start_readers, kill_readers
from mada_progress import ProgressMonitor
from mada_run_logger import RunLogger
from mada_run_state import publish_run_state
from mada_sci import SciRecorder
from mada_software_veto import veto_failed

DRAIN_WAIT = 0.2         # sec, keep readers attached after DAQ enable falls
COUNTER_RESET_WIDTH = 0.1  # sec


def check_protection(config_path):
    """The LV-reset monitor must be up and the software veto released."""
    if not ensure_autoreset_running(config_path):
        raise MonitorError('regulator autoreset monitor is not running')
    if veto_failed():
        raise AdalmError('software veto could not be released (see run/veto.state); stopping')


def run_file(logger, file_id, boards, event_num, roles, sci=None):
    daq_serial, daq_mask = roles[ROLE_DAQ_ENABLE]
    reset_serial, reset_mask = roles[ROLE_COUNTER_RESET]

    publish_run_state(logger.period_dir_abs(), file_id)
    mada_files = logger.mada_file_paths(file_id, boards)
    warn = lambda source, message: logger.warning(file_id, source, message)

    # DAQ enable is low here: it was lowered when the previous file ended (or
    # by the session before the first file), so nothing is acquired while the
    # readers start. Readers that fail to come up are restarted one by one;
    # the counter reset and DAQ enable below then go to all boards together.
    # The SCI acquisition, when asked for, is armed before the readers start so
    # that it is ready when DAQ enable goes up.
    recorder = None
    try:
        if sci:
            print('Starting the SCI acquisition...')
            recorder = SciRecorder(sci, logger.sci_file_path(file_id), warn)
            recorder.start()
        print('Running gigaiwaki (waiting for data flushing)...')
        procs = start_readers(event_num, boards, mada_files, warn)
    except MadaError as e:
        if recorder:
            recorder.stop()
        warn('DAQ', f'ERROR {e}')
        raise

    try:
        print('Resetting counters...')
        run_adalm_control(reset_serial, latch=1, width=COUNTER_RESET_WIDTH, mask=reset_mask)

        print('Latch up DAQ enable...')
        run_adalm_control(daq_serial, latch=1, mask=daq_mask)
        start_time = time.time()

        print('Creating info files...')
        logger.write_info_start(file_id, boards, start_time)

        ProgressMonitor(mada_files, event_num).wait_for_any_exit(procs, recorder.check if recorder else None)

        # Lower DAQ enable before anything else so no event is taken while
        # the readers are being stopped.
        print('Latch down DAQ enable...')
        run_adalm_control(daq_serial, latch=0, mask=daq_mask)
        end_time = time.time()
        time.sleep(DRAIN_WAIT)
    except MadaError as e:
        warn('DAQ', f'ERROR {e}')
        raise
    finally:
        print('Kill gigaiwaki processes...')
        kill_readers(procs)
        if recorder and not recorder.stop():
            warn('SCI', 'WARNING the SCI acquisition did not end cleanly')

    print('Updating info files with end time...')
    logger.finalize_file(file_id, boards, end_time, start_time)


def run_period(config_path, period_id, file_num, event_num, boards, roles, sci=None):
    logger = RunLogger(config_path, period_id)

    for file_id in range(file_num):
        check_protection(config_path)
        print(f'Creating file {file_id} with {event_num} events...')
        run_file(logger, file_id, boards, event_num, roles, sci)
