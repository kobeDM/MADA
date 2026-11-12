#!/usr/bin/env python3

"""The SCI mode: next to the DAQ, one ADALM2000 watches the PMT signal and the
trigger of the DAQ and stores the time of every PMT pulse relative to the
trigger (bin/AdalmAnalogIn). One acquisition process runs per DAQ file."""

import os
import signal
import subprocess
import threading
import time

from mada_adalm_runner import acquire_adalm_lock
from mada_errors import MadaError

MADAHOME = os.environ['MADAHOME']
ANALOG_IN = MADAHOME + '/bin/AdalmAnalogIn'

START_TIMEOUT = 30.0  # sec for the ADALM to be opened and armed
STOP_TIMEOUT = 10.0   # sec for the process to write its file after SIGTERM
STALL_TIMEOUT = 30.0  # sec without a trigger, while DAQ enable is up, that stop the DAQ


class SciError(MadaError):
    """Raised when the SCI acquisition cannot start, dies, or sees no trigger
    while the DAQ is taking events."""


def sci_command(settings, output):
    channels = settings['channels']
    pmt, trigger = settings['pmt'], settings['trigger']
    cmd = [ANALOG_IN, '-s', settings['S/N'], '-o', output,
           '-p', str(channels['pmt']), str(pmt['threshold_V']), pmt['edge'],
           '-t', str(channels['trigger']), str(trigger['threshold_V']), trigger['edge'],
           '-r', settings['range'], '-b', str(settings['buffer_samples']), '-e', str(settings['pre_trigger_samples'])]
    if settings['save_waveform']:
        cmd.append('-w')
    return cmd


class SciRecorder:
    """One acquisition process: start() returns when the ADALM is armed,
    check() is called while the DAQ takes events, stop() ends it and lets it
    write its file. simulate (trigger rate in Hz) runs without an ADALM."""

    def __init__(self, settings, output, warn, simulate=None):
        self.cmd = sci_command(settings, output)
        if simulate:
            self.cmd = [ANALOG_IN, '-o', output] + self.cmd[5:] + ['--simulate', str(simulate)]
        self.output = output
        self.status_path = output[:-5] + '.status' if output.endswith('.root') else output + '.status'
        self.warn = warn
        self.simulate = bool(simulate)
        self.proc = None
        self._ready = threading.Event()
        self._count = 0
        self._changed = None

    def _read_output(self):
        for line in self.proc.stdout:
            line = line.strip()
            if line == 'READY':
                self._ready.set()
            elif line:
                print(f'[SCI] {line}', flush=True)
                if line.startswith(('ERROR', 'WARNING')):
                    self.warn('SCI', line)

    def start(self):
        # Two processes that open ADALMs at once can make one of them fail, so
        # the open is done under the lock of the DAQ's own ADALM calls.
        lock = None if self.simulate else acquire_adalm_lock()
        try:
            self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            threading.Thread(target=self._read_output, daemon=True).start()

            deadline = time.time() + START_TIMEOUT
            while not self._ready.wait(0.2):
                if self.proc.poll() is not None:
                    raise SciError(f'SCI acquisition exited with code {self.proc.returncode} while starting')
                if time.time() > deadline:
                    self.proc.kill()
                    raise SciError(f'SCI acquisition did not get ready within {START_TIMEOUT:.0f} s')
        finally:
            if lock:
                lock.close()

    def _triggers(self):
        try:
            with open(self.status_path) as f:
                for line in f:
                    key, _, value = line.partition(' ')
                    if key == 'triggers':
                        return int(value)
        except (OSError, ValueError):
            pass
        return None

    def check(self):
        """Raises SciError when the process died or saw no trigger for STALL_TIMEOUT."""
        if self.proc.poll() is not None:
            raise SciError(f'SCI acquisition exited with code {self.proc.returncode}')

        now = time.time()
        count = self._triggers()
        if self._changed is None or (count is not None and count != self._count):
            self._changed = now
            self._count = count if count is not None else self._count
        elif now - self._changed > STALL_TIMEOUT:
            raise SciError(f'the SCI ADALM saw no DAQ trigger for {STALL_TIMEOUT:.0f} s while DAQ enable is up')

    def stop(self):
        """End the process (it writes its file on SIGTERM); returns False when it had to be killed."""
        if self.proc is None or self.proc.poll() is not None:
            return self.proc is None or self.proc.returncode == 0

        self.proc.send_signal(signal.SIGTERM)
        try:
            self.proc.wait(timeout=STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
            self.warn('SCI', f'WARNING the SCI acquisition did not stop within {STOP_TIMEOUT:.0f} s and was killed; {self.output} may be incomplete')
            return False

        try:
            os.remove(self.status_path)
        except OSError:
            pass
        return self.proc.returncode == 0
