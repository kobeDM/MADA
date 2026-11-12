#!/usr/bin/env python3

"""Background polling of daq-client (spec 2026-11-12_3.md sections 3.4 and
4). Runs continuously regardless of how many browsers are connected, keeps
mada_server_state.state up to date and raises notifications (section 3.4)
into the DB on the edges the spec lists: an abnormal exit, a period
boundary, connection loss/recovery, a monitor going bad, an invalid file,
and stale progress.

Cursors that gate notifications (the last-notified DAQ exit, the files
cursor) are persisted in the DB, not just kept in memory, so a server
restart doesn't re-raise a notification it already raised (2026-11-12
integration review, 2.4)."""

import asyncio
import time

import mada_server_db as db
from mada_server_client import DaqClientError

TICK_S = 0.2
STATUS_INTERVAL_S = 2.0
PROGRESS_INTERVAL_S = 1.0
WARNINGS_INTERVAL_S = 5.0
FILES_INTERVAL_S = 10.0
BACKOFF_MIN_S = 2.0
BACKOFF_MAX_S = 30.0
RUNNING_PHASES = ('running', 'starting', 'stopping')
FIRST_FILE_ID = -1  # "after" is exclusive (API contract 4.7), and file_id starts at 0


class Poller:
    def __init__(self, client, state):
        self.client = client
        self.state = state
        self._status_backoff = BACKOFF_MIN_S
        self._next_status = 0.0
        self._next_progress = 0.0
        self._next_warnings = 0.0
        self._next_files = 0.0
        self._prev_daq_by_run = {}  # run -> last-seen daq dict, for period-transition wording
        self._notified_exit_time = db.get_last_notified_exit_time()
        self._prev_autoreset_running = None
        self._prev_veto_failed = None
        self._prev_stale = None
        self._current_run_period = None  # (run, period) that warnings/files polling follows

    async def run(self, stop_event):
        while not stop_event.is_set():
            now = time.monotonic()
            if now >= self._next_status:
                await self._poll_status()
                now = time.monotonic()
                interval = STATUS_INTERVAL_S if self.state.connected else self._status_backoff
                self._next_status = now + interval

            if self.state.connected:
                if now >= self._next_progress:
                    if (self.state.status or {}).get('phase') == 'running':
                        await self._poll_progress()
                    self._next_progress = now + PROGRESS_INTERVAL_S
                if now >= self._next_warnings:
                    await self._poll_warnings()
                    self._next_warnings = now + WARNINGS_INTERVAL_S
                if now >= self._next_files:
                    await self._poll_files()
                    self._next_files = now + FILES_INTERVAL_S

            self.state.broadcast()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=TICK_S)
            except asyncio.TimeoutError:
                pass

    # -- /status ------------------------------------------------------------

    async def _poll_status(self):
        try:
            status = await self.client.status()
        except DaqClientError as e:
            self._on_status_failure(e)
            return
        await self._on_status_success(status)

    def _on_status_failure(self, error):
        self.state.consecutive_failures += 1
        self.state.last_error = error.message
        if self.state.consecutive_failures >= 3:
            if self.state.connected is True:
                db.add_notification('connection_lost', 'Lost connection to daq-client')
            self.state.connected = False
            self._status_backoff = min(self._status_backoff * 2, BACKOFF_MAX_S)

    async def _on_status_success(self, status):
        was_connected = self.state.connected
        self.state.connected = True
        self.state.consecutive_failures = 0
        self.state.last_error = None
        self.state.last_success_at = time.time()
        self.state.status = status
        self._status_backoff = BACKOFF_MIN_S
        if was_connected is False:
            db.add_notification('connection_restored', 'Connection to daq-client restored')

        self._check_last_exit(status)
        self._check_period(status)
        self._check_monitor(status)

        phase, daq = status.get('phase'), status.get('daq')
        new_target = (daq.get('run'), daq.get('period')) if (phase in RUNNING_PHASES and daq) else None

        # Fetch one last round of warnings for the (run, period) we are
        # leaving before switching away, so a warning logged in the last few
        # seconds before a stop/period boundary isn't dropped on the floor
        # (2026-11-12 integration review, 2.5).
        if new_target != self._current_run_period and self._current_run_period is not None:
            await self._drain_warnings(*self._current_run_period)
        self._current_run_period = new_target

    def _check_last_exit(self, status):
        last_exit = status.get('last_exit')
        if not last_exit:
            return
        exit_time = last_exit.get('time')
        if exit_time == self._notified_exit_time:
            return
        self._notified_exit_time = exit_time
        db.set_last_notified_exit_time(exit_time)
        if last_exit.get('reason') in ('error', 'crashed'):
            db.add_notification(
                'daq_exit',
                f"DAQ exited abnormally ({last_exit.get('reason')}): {last_exit.get('message') or ''}")

    def _check_period(self, status):
        daq = status.get('daq')
        if not daq:
            return
        run, period = daq.get('run'), daq.get('period')
        if run is None or period is None:
            return
        prev_daq = self._prev_daq_by_run.get(run)
        if prev_daq is not None and period > prev_daq.get('period'):
            self._notify_period_ended(run, prev_daq)
        self._prev_daq_by_run[run] = daq

    def _notify_period_ended(self, run, prev_daq):
        """A period boundary doesn't always mean the period actually
        finished: stopping mid-period and starting again also bumps the
        period number for the next one. Only call it "completed" when the old
        period actually reached file_num valid files (2026-11-12 integration
        review, 2.6)."""
        prev_period = prev_daq.get('period')
        valid_files, file_num = prev_daq.get('valid_files'), prev_daq.get('file_num')
        if valid_files is not None and file_num is not None and valid_files >= file_num:
            db.add_notification('period_done', f"run {run}: period {prev_period} completed")
        else:
            db.add_notification(
                'period_incomplete',
                f"run {run}: period {prev_period} ended by a stop ({valid_files}/{file_num} files)")

    def _check_monitor(self, status):
        phase = status.get('phase')
        monitor = status.get('monitor') or {}
        autoreset_running = monitor.get('autoreset_running')
        veto_failed = (monitor.get('veto') or {}).get('failed')

        if phase in ('running', 'starting') and autoreset_running is False \
                and self._prev_autoreset_running is not False:
            db.add_notification('autoreset_down', 'The LV overcurrent auto-reset monitor is not running')
        if veto_failed and not self._prev_veto_failed:
            db.add_notification('veto_failed', 'The software veto has failed')

        self._prev_autoreset_running = autoreset_running
        self._prev_veto_failed = veto_failed

    # -- /progress ------------------------------------------------------------

    async def _poll_progress(self):
        try:
            progress = await self.client.progress()
        except DaqClientError:
            return
        self.state.progress = progress
        stale = progress.get('stale')
        if stale and not self._prev_stale:
            db.add_notification('progress_stale', f"Progress updates have stopped (file_id={progress.get('file_id')})")
        self._prev_stale = stale

    # -- warnings / files (feed the live cache and raise invalid-file alerts) --

    async def _poll_warnings(self):
        target = self._current_run_period
        if not target or target[0] is None or target[1] is None:
            return
        await self._drain_warnings(*target)

    async def _drain_warnings(self, run, period):
        after = db.get_warnings_cursor(run, period)
        try:
            result = await self.client.warnings(run, period, after=after, limit=200)
        except DaqClientError:
            return
        records = result.get('records', [])
        if not records:
            return
        self.state.push_warnings(records)
        db.set_warnings_cursor(run, period, max(r['t'] for r in records))

    async def _poll_files(self):
        target = self._current_run_period
        if not target or target[0] is None or target[1] is None:
            return
        run, period = target
        after = db.get_files_cursor(run, period)
        if after is None:
            after = FIRST_FILE_ID
        try:
            result = await self.client.files(run, period, after=after, limit=1000)
        except DaqClientError:
            return
        max_finished = after
        for f in result.get('files', []):
            if f.get('end') is None:
                continue
            max_finished = max(max_finished, f['file_id'])
            if not f.get('valid', True):
                db.add_notification(
                    'file_invalid',
                    f"run {run} per{period:04d} file {f['file_id']}: invalid ({f.get('invalid_reason')})")
        if max_finished != after:
            db.set_files_cursor(run, period, max_finished)
