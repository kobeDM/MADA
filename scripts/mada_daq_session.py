#!/usr/bin/env python3

"""One DAQ session: power the boards up, acquire period after period until
stopped or failed, then shut everything down."""

import traceback

from mada_adalm_roles import daq_roles, ROLE_DAQ_ENABLE
from mada_adalm_runner import run_adalm_control, AdalmError
from mada_config import load_config, active_boards
from mada_daemon import switch_log
from mada_daq_killer import run_daq_killer
from mada_encoder_power import run_encoder_power_up, run_encoder_power_down
from mada_errors import MadaError
from mada_file_cycle import run_period
from mada_kill_adalms import run_kill_adalms
from mada_kill_modules import run_kill_modules
from mada_run_logger import RunLogger
from mada_run_state import clear_run_state


def _shutdown(config_path, daq_role):
    """Each step is guarded so that a failure in one does not skip the next or
    hide the error that stopped the DAQ."""
    clear_run_state()

    try:
        run_daq_killer(config_path)
    except Exception as e:
        print(f'WARNING: could not finalize the last file ({e}).')

    # Close the scaler period: it is updated on the falling edge of DAQ enable.
    try:
        serial, mask = daq_role
        run_adalm_control(serial, latch=0, mask=mask)
    except AdalmError as e:
        print(f'WARNING: could not latch down DAQ enable on exit ({e}).')

    try:
        run_encoder_power_down(config_path)
    except Exception as e:
        print(f'WARNING: power down failed ({e}); check that the regulators are off.')


def run_daq(config_path, file_num, event_num, first_period, daemon, calin=None, sci=None):
    config_load = load_config(config_path)
    boards = active_boards(config_load)
    if calin:
        boards = [(board_id, ip) for board_id, ip in boards if ip == calin[0]]
    else:
        for board_id, ip in boards:
            print(f'Starting DAQ for board {board_id} at IP {ip}')

    roles = daq_roles(config_load)

    run_kill_modules()
    run_kill_adalms()

    try:
        run_encoder_power_up(config_path, calin=calin, require_monitor=True)

        print('DAQ is running... Press Ctrl+C to stop.')
        print('Latch down DAQ enable (initial)...')
        serial, mask = roles[ROLE_DAQ_ENABLE]
        run_adalm_control(serial, latch=0, mask=mask)

        period = first_period
        while True:
            print('New period created : per' + str(period).zfill(4))
            run_period(config_path, period, file_num, event_num, boards, roles, sci)
            period = RunLogger.new_period()
            if daemon:
                switch_log(period)
    except KeyboardInterrupt:
        print('Keyboard interrupt received. Stopping DAQ...')
        raise
    except MadaError as e:
        print(f'FATAL: {e}. Stopping DAQ...')
        raise
    except Exception:
        print('FATAL: unexpected error. Stopping DAQ...')
        traceback.print_exc()
        raise
    finally:
        _shutdown(config_path, roles[ROLE_DAQ_ENABLE])
