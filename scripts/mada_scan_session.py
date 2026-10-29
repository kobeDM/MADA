#!/usr/bin/env python3

"""One scan session: switch on the regulators that are off, raise DAQ enable,
run the DAC/Vth correction of every selected board in parallel (the boards
share one external trigger), and leave the boards with their configured
settings again; the regulators that the session switched on are switched off
again. The corrected DAC files are written into the output directory only;
the config is not touched."""

import glob
import json
import os
import shutil
import subprocess
import threading
import time

import mada_scan_tools as tools
from mada_adalm_roles import adalm_role, ROLE_DAQ_ENABLE
from mada_adalm_runner import run_adalm_control, AdalmError
from mada_ap_state import get_ap_state
from mada_config import load_config, active_boards, validate_boards, latch_up_detect_enabled
from mada_process import find_processes
from mada_set_ap import run_set_ap
from mada_scan_board import scan_board
from mada_scan_progress import ScanProgress
from mada_errors import MadaError
from mada_scan_tools import ScanError

MADAHOME = os.environ['MADAHOME']
SET_ALL_DAC = MADAHOME + '/bin/SetAllDAC'
BUSY_PROGRAMS = ['MadaIwaki', 'mada.py']
RESTORE_TIMEOUT = 150.0  # sec for SetAllDAC (RBCP retries a silent board for up to 100 s)


def next_scan_dir():
    numbers = [int(path[-4:]) for path in glob.glob('scan_run[0-9][0-9][0-9][0-9]')]
    return 'scan_run' + str(max(numbers) + 1 if numbers else 0).zfill(4)


def select_boards(config, names):
    boards = active_boards(config)
    if not names:
        return boards

    selected = [(name, ip) for name, ip in boards if name in names or ip in names]
    unknown = set(names) - {name for name, _ in selected} - {ip for _, ip in selected}
    if unknown:
        raise ScanError('not an active board: ' + ', '.join(sorted(unknown)))
    return selected


def _check_idle():
    busy = find_processes(BUSY_PROGRAMS)
    if busy:
        raise ScanError('a DAQ is running (PID ' + ', '.join(str(p.pid) for p in busy) + '); stop it before scanning')


def _write_settings(name, entry):
    """Write the configured Vth, DAC values and bias to the board. Returns an
    error text, or None on success."""
    cmd = [SET_ALL_DAC, entry['IP'], str(entry['Vth']), entry['DACfile'], str(entry['bias'])]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=RESTORE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return f'SetAllDAC for {name} timed out'
    return None if result.returncode == 0 else f'SetAllDAC for {name} failed'


def _restore_board(name, entry):
    error = _write_settings(name, entry)
    if error:
        print(f'WARNING: {error}; set its DAC/Vth again with mada_set_all_dac.py.')


def _power_up(config_path, config, boards, powered):
    """Switch the regulator on for the boards that are off and write their
    configured settings. The boards switched on are added to powered so that
    they are switched off again at the end."""
    if latch_up_detect_enabled(config):
        print('WARNING: latch-up detection is not enabled during a scan.')

    for name, ip in boards:
        if get_ap_state(ip):
            print(f'{name}: regulator is already on.')
            continue

        print(f'{name}: activating the regulator...')
        powered.append((name, ip))
        run_set_ap(config_path, io=1, target_ip=ip, require_monitor=True)
        error = _write_settings(name, config['gigaIwaki'][name])
        if error:
            raise ScanError(error)


def _power_down(config_path, powered):
    for name, ip in powered:
        try:
            print(f'{name}: deactivating the regulator...')
            run_set_ap(config_path, io=0, target_ip=ip)
        except MadaError as e:
            print(f'WARNING: could not switch {name} off ({e}); check that its regulator is off.')


def _board_worker(name, entry, outdir, params, results, progress):
    try:
        results[name] = scan_board(name, entry['IP'], entry['Vth'], entry['DACfile'], f'{outdir}/{name}', params, progress)
        progress.finish()
    except ScanError as e:
        progress.say(f'FAILED: {e}')
        progress.finish(failed=True)
        results[name] = {'board': name, 'error': str(e)}
    except Exception as e:
        progress.say(f'FAILED: unexpected error: {e!r}')
        progress.finish(failed=True)
        results[name] = {'board': name, 'error': repr(e)}


def _run_workers(boards, config, outdir, params):
    results = {}
    progress = ScanProgress([name for name, _ in boards])
    threads = [threading.Thread(target=_board_worker, args=(name, config['gigaIwaki'][name], outdir, params, results, progress.board(name)))
               for name, _ in boards]
    progress.start()
    try:
        for t in threads:
            t.start()
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=0.5)
    finally:
        progress.stop()
    return results


def _report(results, outdir):
    print('\n=== Scan summary ===')
    failed = 0
    for name, s in results.items():
        if 'error' in s:
            failed += 1
            print(f"{name}: FAILED ({s['error']})")
            continue

        last = s['iterations'][-1]
        rms = last['rms']
        print(f"{name}: slope {s['slope']:.1f} Vth/DAC, Vth center rms {rms if rms is None else round(rms, 1)}, "
              f"{last['ok']} channels fitted, unfitted {len(s['unfitted_channels'])}")
        if s['unfitted_channels']:
            print('    unfitted channels: ' + ', '.join(f'{ch}({cls})' for ch, cls in sorted(s['unfitted_channels'].items())))
        for w in s['warnings']:
            print('    WARNING: ' + w)
        shutil.copy(s['final_dac'], f'{outdir}/{name}.dac')
        print(f'    corrected DAC file: {outdir}/{name}.dac')

    with open(outdir + '/scan_summary.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    return failed


def run_scan(config_path, params, names=None, outdir=None):
    """Returns the number of boards that failed."""
    config = load_config(config_path)
    validate_boards(config)
    boards = select_boards(config, names)
    serial, mask = adalm_role(config, ROLE_DAQ_ENABLE)
    _check_idle()

    outdir = outdir or next_scan_dir()
    os.makedirs(outdir, exist_ok=True)
    print(f'Scan output: {outdir}')
    print('Boards: ' + ', '.join(f'{name} ({ip})' for name, ip in boards))

    started = time.time()
    results = {}
    powered = []
    try:
        _power_up(config_path, config, boards, powered)
        print('Raising DAQ enable...')
        run_adalm_control(serial, latch=1, mask=mask)
        results = _run_workers(boards, config, outdir, params)
    finally:
        tools.terminate_all()
        try:
            run_adalm_control(serial, latch=0, mask=mask)
        except AdalmError as e:
            print(f'WARNING: could not latch down DAQ enable ({e}).')
        for name, _ in boards:
            if (name, config['gigaIwaki'][name]['IP']) not in powered:
                _restore_board(name, config['gigaIwaki'][name])
        _power_down(config_path, powered)

    print(f'Scan took {time.time() - started:.0f} s.')
    return _report(results, outdir)
