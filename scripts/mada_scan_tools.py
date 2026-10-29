#!/usr/bin/env python3

"""Wrappers for the scan binaries (ScanAcquire, ScanFit, ScanCorrect). Every
call is logged to the board's scan log; a failing binary raises ScanError."""

import csv
import os
import subprocess
import tempfile
import threading
import time

from mada_errors import MadaError

MADAHOME = os.environ['MADAHOME']
ACQUIRE = MADAHOME + '/bin/ScanAcquire'
FIT = MADAHOME + '/bin/ScanFit'
CORRECT = MADAHOME + '/bin/ScanCorrect'

POLL_INTERVAL = 1.0      # sec between progress polls of a running binary
FIT_TIMEOUT = 600.0      # sec for one ScanFit
CORRECT_TIMEOUT = 60.0   # sec for one ScanCorrect
ACQUIRE_MARGIN = 120.0   # sec added to the estimated acquisition time

_running = set()
_running_lock = threading.Lock()


class ScanError(MadaError):
    """Raised when a scan binary fails or its result cannot be used."""


def terminate_all():
    """Stop every scan binary that is still running (Ctrl+C, fatal error)."""
    with _running_lock:
        procs = list(_running)
    for proc in procs:
        proc.terminate()


def _run(cmd, log_path, timeout, name, poll=None):
    """Run a binary and return its output; poll() is called every POLL_INTERVAL
    while it runs."""
    with open(log_path, 'a', encoding='utf-8') as log, tempfile.TemporaryFile('w+') as out:
        log.write('$ ' + ' '.join(cmd) + '\n')
        log.flush()
        proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, text=True)
        with _running_lock:
            _running.add(proc)
        deadline = time.time() + timeout
        try:
            while True:
                try:
                    proc.wait(timeout=POLL_INTERVAL)
                    break
                except subprocess.TimeoutExpired:
                    if poll:
                        poll()
                    if time.time() > deadline:
                        proc.kill()
                        proc.wait()
                        log.write(f'(killed after {timeout:.0f} s)\n')
                        raise ScanError(f'{name} did not finish within {timeout:.0f} s')
        finally:
            with _running_lock:
                _running.discard(proc)
        out.seek(0)
        output = out.read()
        log.write(output)

    if proc.returncode != 0:
        lines = [line for line in output.splitlines() if line.strip()]
        raise ScanError(f'{name} failed (code {proc.returncode}): ' + (lines[-1] if lines else 'no output'))
    return output


def key_values(output):
    """{key: value} of the 'key: value' lines; repeated keys give lists."""
    result = {}
    for line in output.splitlines():
        key, sep, value = line.partition(': ')
        if not sep or ' ' in key:
            continue
        result.setdefault(key, []).append(value.strip())
    return {key: (values[0] if len(values) == 1 else values) for key, values in result.items()}


def count_points(outdir):
    """Scan points ScanAcquire has written so far."""
    try:
        with open(outdir + '/scan_points.csv') as f:
            return max(sum(1 for _ in f) - 1, 0)
    except OSError:
        return 0


def acquire(ip, mode, outdir, start, end, step, extra, events, point_timeout, settle, log_path, on_points=None):
    """Run ScanAcquire. extra is ['-d', dacfile] (mode vth) or ['-v', vth] (mode dac);
    on_points(n) is called with the number of points done while it runs."""
    points = (end - start) // step + 1
    estimate = points * (2 * settle + 2.0 + point_timeout)
    cmd = [ACQUIRE, ip, mode, outdir, str(start), str(end), str(step)] + [str(x) for x in extra]
    cmd += ['-n', str(events), '-t', str(point_timeout), '-s', str(settle)]
    poll = (lambda: on_points(count_points(outdir))) if on_points else None
    _run(cmd, log_path, estimate + ACQUIRE_MARGIN, f'ScanAcquire {mode} scan of {ip}', poll)
    if on_points:
        on_points(points)


def fit(outdir, mode, log_path, target=None, level=0.5, metric='rate'):
    """Run ScanFit (target: the working Vth drawn into the plot; level: the
    fraction of the noise transition the channels are aligned at, counted in
    clocks with a hit ('rate') or events with a hit ('occupancy')); returns
    {'classes': {class: n}, 'centers': [aligned positions of the ok channels], 'by_channel': {ch: class}}."""
    cmd = [FIT, outdir, mode, str(-1 if target is None else target), str(level), metric]
    _run(cmd, log_path, FIT_TIMEOUT, f'ScanFit of {outdir}')
    return read_fit(outdir)


def read_fit(outdir):
    classes = {}
    centers = []
    with open(outdir + '/fit_result.csv', newline='') as f:
        for row in csv.DictReader(f):
            classes[row['class']] = classes.get(row['class'], 0) + 1
            if row['class'] == 'ok':
                centers.append(float(row.get('aligned', row['center'])))
    return {'classes': classes, 'centers': centers, 'by_channel': channel_classes(outdir)}


def channel_classes(outdir):
    with open(outdir + '/fit_result.csv', newline='') as f:
        return {int(row['ch']): row['class'] for row in csv.DictReader(f)}


def correct_dac(fit_csv, reference, out_dac, log_path):
    return key_values(_run([CORRECT, 'dac', fit_csv, reference or 'none', out_dac], log_path, CORRECT_TIMEOUT, 'ScanCorrect dac'))


def measure_slope(fit_csv0, vth0, fit_csv1, vth1, log_path):
    return key_values(_run([CORRECT, 'slope', fit_csv0, str(vth0), fit_csv1, str(vth1)], log_path, CORRECT_TIMEOUT, 'ScanCorrect slope'))


def refine_dac(fit_csv, dac_in, slope, dac_out, target, log_path):
    cmd = [CORRECT, 'refine', fit_csv, dac_in, str(slope), dac_out, str(target)]
    return key_values(_run(cmd, log_path, CORRECT_TIMEOUT, 'ScanCorrect refine'))


def dac_polarity(outdir):
    """Median of the occupancy at the start minus the end of a DAC scan over its
    fitted channels: positive when the hits are at low DAC values."""
    values = []
    with open(outdir + '/fit_result.csv', newline='') as f:
        for row in csv.DictReader(f):
            if row['class'] == 'ok':
                values.append(float(row['rate_start']) - float(row['rate_end']))
    if not values:
        raise ScanError(f'no fitted channel in {outdir}')
    values.sort()
    return values[len(values) // 2]
