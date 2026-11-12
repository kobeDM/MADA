#!/usr/bin/env python3

"""The scaler (runScaler on the Zybo, started over ssh). runScaler serves one
period: it writes <output_dir>/perNNNN, one line per falling edge of DAQ
enable, and ignores the first edge it sees. So it is started for every period
while DAQ enable is low (before the first file) and stopped after the last
file. The output directory is shared with this PC (NFS; the Zybo mounts it
under another path, remote_output_root), so the lines can be counted here
without ssh."""

import os
import shlex
import subprocess
import time

from mada_config import scaler_settings
from mada_daemon import run_name
from mada_errors import MadaError
from mada_run_state import write_json

MADAHOME = os.environ['MADAHOME']
STATE_PATH = MADAHOME + '/run/mada_scaler.json'
REMOTE_LOG = '/tmp/mada_runScaler.log'

FILE_WAIT = 5.0    # sec for the output file to appear after the start
LINE_WAIT = 3.0    # sec for the scaler to write the line of a finished file
STOP_WAIT = 3.0    # sec for the process to end after SIGTERM
POLL = 0.1         # sec
SSH_MARGIN = 10.0  # sec added to the connect timeout for one ssh call


class ScalerError(MadaError):
    """The scaler could not be started, or it does not record the files."""


def count_lines(path):
    try:
        with open(path, 'rb') as f:
            return f.read().count(b'\n')
    except FileNotFoundError:
        return 0


class ScalerRunner:
    def __init__(self, settings, run=None):
        self.ssh = settings['ssh']
        self.command = settings['command']
        run = run or run_name()
        self.out_dir = os.path.join(settings['output_root'], run)
        self.remote_out_dir = os.path.join(settings.get('remote_output_root') or settings['output_root'], run)
        self.period = None
        self.pid = None

    @classmethod
    def from_config(cls, config):
        settings = scaler_settings(config)
        return cls(settings) if settings else None

    def out_file(self, period=None):
        return f'{self.out_dir}/per{(self.period if period is None else period):04d}'

    def _ssh(self, remote_command):
        cmd = ['ssh', '-i', self.ssh['identity_file'], '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
               '-o', f"ConnectTimeout={self.ssh['connect_timeout']}", self.ssh['host'], remote_command]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                  timeout=self.ssh['connect_timeout'] + SSH_MARGIN)
        except subprocess.TimeoutExpired:
            raise ScalerError(f"ssh to {self.ssh['host']} timed out")
        except OSError as e:
            raise ScalerError(f'cannot run ssh: {e}')

    def _write_state(self, state):
        try:
            write_json(STATE_PATH, {'state': state, 'period': self.period, 'pid': self.pid,
                                    'host': self.ssh['host'], 'time': time.time()})
        except OSError as e:
            print(f'WARNING: could not write {STATE_PATH} ({e})')

    def preflight(self):
        """Fail early (before the DAQ is started) when the scaler cannot be used."""
        done = self._ssh(f'test -x {shlex.quote(self.command)}')
        if done.returncode == 255:
            raise ScalerError(f"cannot ssh to {self.ssh['host']}: {done.stderr.strip()}")
        if done.returncode != 0:
            raise ScalerError(f"{self.command} is not executable on {self.ssh['host']}")

    def clean_stale(self):
        """Stop a runScaler left over from an earlier run."""
        done = self._ssh('pkill -x runScaler; true')
        if done.returncode != 0:
            raise ScalerError(f"cannot clean up the scaler on {self.ssh['host']}: {done.stderr.strip()}")

    def start(self, period):
        """Start runScaler for the period; DAQ enable must be low."""
        self.period = period
        self.pid = None
        out_file = self.out_file()
        if os.path.exists(out_file):
            raise ScalerError(f'{out_file} already exists; runScaler would overwrite it')
        try:
            os.makedirs(self.out_dir, exist_ok=True)
        except OSError as e:
            raise ScalerError(f'cannot create {self.out_dir}: {e}')

        remote = (f'nohup {shlex.quote(self.command)} {shlex.quote(self.remote_out_dir)} {period} '
                  f'> {REMOTE_LOG} 2>&1 < /dev/null & echo $!')
        done = self._ssh(remote)
        lines = done.stdout.split()
        if done.returncode != 0 or not lines or not lines[-1].isdigit():
            raise ScalerError(f"cannot start runScaler on {self.ssh['host']}: {done.stderr.strip() or done.stdout.strip()}")
        self.pid = int(lines[-1])

        deadline = time.time() + FILE_WAIT
        while not os.path.exists(out_file):
            if time.time() > deadline:
                self.stop()
                raise ScalerError(f'runScaler did not create {out_file} (see {REMOTE_LOG} on {self.ssh["host"]})')
            time.sleep(POLL)
        self._write_state('running')
        print(f'Scaler started for per{period:04d} (PID {self.pid} on {self.ssh["host"]}).')

    def verify_file(self, file_id):
        """The scaler must have written the line of file file_id by now."""
        expected = file_id + 1
        deadline = time.time() + LINE_WAIT
        while count_lines(self.out_file()) < expected:
            if time.time() > deadline:
                raise ScalerError(f'the scaler did not record file {file_id} ({count_lines(self.out_file())} lines in '
                                  f'{self.out_file()}, expected {expected})')
            time.sleep(POLL)
        if count_lines(self.out_file()) > expected:
            raise ScalerError(f'the scaler has more lines than files in {self.out_file()} (expected {expected})')

    def stop(self):
        """Stop the runScaler of the current period. Never raises; returns False
        when it could not be confirmed to be stopped (the PID is kept, so it
        can be tried again)."""
        if self.pid is None:
            return True
        pid = self.pid
        try:
            check = f'ps -p {pid} -o comm= | grep -qx runScaler'
            done = self._ssh(f'if {check}; then kill {pid}; for i in $(seq 1 {int(STOP_WAIT / POLL)}); do {check} || exit 0; sleep {POLL}; done; exit 1; fi')
            ok = done.returncode == 0
        except ScalerError as e:
            print(f'WARNING: {e}')
            ok = False
        if ok:
            self.pid = None
        self._write_state('stopped' if ok else 'failed')
        if not ok:
            print(f"WARNING: could not confirm that runScaler (PID {pid}) stopped on {self.ssh['host']}.")
        return ok
