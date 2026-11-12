#!/usr/bin/env python3

"""Unit tests for the Poller's notification logic, against a fake DaqClient
instead of a real daq-client -- the structure the 2026-11-12 integration
review (section 4) asked for. Run with:

    python3 -m unittest discover -s server/tests -t server

Covers the fixes from that review: 2.1 (files "after" starts at -1, not 0,
so file_id 0 isn't skipped), 2.4 (notified-exit and files cursors survive a
restart), 2.5 (one last warnings fetch for the (run, period) being left),
and 2.6 (a period boundary only reads "completed" when the old period actually
reached file_num)."""

import asyncio
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mada_server_db as db
from mada_server_poller import Poller


class FakeClient:
    """Returns canned data instead of calling a real daq-client. `files_by`
    and `warnings_by` are keyed by (run, period); `warnings_calls` records
    every (run, period, after) a test wants to assert against."""

    def __init__(self):
        self.files_by = {}
        self.warnings_by = {}
        self.warnings_calls = []

    async def files(self, run, period, after=None, limit=None):
        files = self.files_by.get((run, period), [])
        after = -1 if after is None else after
        return {'files': [f for f in files if f['file_id'] > after]}

    async def warnings(self, run, period, after=None, limit=None):
        self.warnings_calls.append((run, period, after))
        records = self.warnings_by.get((run, period), [])
        if after is not None:
            records = [r for r in records if r['t'] > after]
        return {'records': records}


class FakeState:
    def __init__(self):
        self.connected = None
        self.consecutive_failures = 0
        self.last_error = None
        self.last_success_at = None
        self.status = None
        self.progress = None
        self.recent_warnings = []

    def push_warnings(self, records):
        self.recent_warnings.extend(records)

    def broadcast(self):
        pass


def run_async(coro):
    return asyncio.run(coro)


def make_status(phase, run=None, period=None, valid_files=None, file_num=None,
                 stop_requested_at=None, last_exit=None):
    daq = None
    if run is not None:
        daq = {'run': run, 'period': period, 'valid_files': valid_files, 'file_num': file_num,
               'started_at': 0.0, 'stop_requested_at': stop_requested_at,
               'file_id': 0, 'event_num': 1000, 'sci': False, 'pid': 1, 'boards': []}
    return {
        'api_version': 1, 'time': 0.0, 'phase': phase, 'blocked_by': None, 'latest_run': run,
        'daq': daq, 'monitor': {'autoreset_running': True, 'veto': {'failed': False, 'asserted': False}},
        'last_exit': last_exit,
    }


class PollerTestCase(unittest.TestCase):
    def setUp(self):
        fd, self._db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db.init_db(self._db_path)

    def tearDown(self):
        os.remove(self._db_path)

    def notifications(self):
        return db.list_notifications(include_acknowledged=True, limit=1000)


class FilesAfterDefaultTest(PollerTestCase):
    """2.1: file_id 0 must not be skipped on the first poll."""

    def test_file_zero_is_checked(self):
        client = FakeClient()
        client.files_by[('20261112', 3)] = [
            {'file_id': 0, 'end': 1.0, 'valid': False, 'invalid_reason': 'sim'},
        ]
        poller = Poller(client, FakeState())
        poller._current_run_period = ('20261112', 3)

        run_async(poller._poll_files())

        kinds = [n['kind'] for n in self.notifications()]
        self.assertIn('file_invalid', kinds)


class RestartDedupTest(PollerTestCase):
    """2.4: a notification already raised before a restart must not be
    raised again by a fresh Poller reading the same DB."""

    def test_exit_not_renotified_after_restart(self):
        client = FakeClient()
        poller = Poller(client, FakeState())
        status = make_status('idle', last_exit={'reason': 'error', 'message': 'boom', 'time': 123.0,
                                                 'run': '20261112', 'period': 3})

        run_async(poller._on_status_success(status))
        self.assertEqual(len([n for n in self.notifications() if n['kind'] == 'daq_exit']), 1)

        # Simulate a server restart: a brand new Poller, same DB.
        restarted = Poller(client, FakeState())
        run_async(restarted._on_status_success(status))

        self.assertEqual(len([n for n in self.notifications() if n['kind'] == 'daq_exit']), 1)

    def test_files_not_rechecked_after_restart(self):
        client = FakeClient()
        client.files_by[('20261112', 3)] = [
            {'file_id': 0, 'end': 1.0, 'valid': False, 'invalid_reason': 'sim'},
        ]
        poller = Poller(client, FakeState())
        poller._current_run_period = ('20261112', 3)
        run_async(poller._poll_files())
        self.assertEqual(len([n for n in self.notifications() if n['kind'] == 'file_invalid']), 1)

        restarted = Poller(client, FakeState())
        restarted._current_run_period = ('20261112', 3)
        run_async(restarted._poll_files())
        self.assertEqual(len([n for n in self.notifications() if n['kind'] == 'file_invalid']), 1)


class PeriodWordingTest(PollerTestCase):
    """2.6: a period boundary only reads "completed" when the old period actually
    reached file_num; stopping mid-period gets different wording."""

    def test_full_period_reads_done(self):
        client = FakeClient()
        poller = Poller(client, FakeState())
        run_async(poller._on_status_success(
            make_status('running', run='20261112', period=3, valid_files=512, file_num=512)))
        run_async(poller._on_status_success(
            make_status('running', run='20261112', period=4, valid_files=1, file_num=512)))

        kinds = [n['kind'] for n in self.notifications()]
        self.assertIn('period_done', kinds)
        self.assertNotIn('period_incomplete', kinds)

    def test_stopped_mid_period_reads_incomplete(self):
        client = FakeClient()
        poller = Poller(client, FakeState())
        run_async(poller._on_status_success(
            make_status('running', run='20261112', period=3, valid_files=3, file_num=512)))
        run_async(poller._on_status_success(
            make_status('running', run='20261112', period=4, valid_files=1, file_num=512)))

        kinds = [n['kind'] for n in self.notifications()]
        self.assertIn('period_incomplete', kinds)
        self.assertNotIn('period_done', kinds)


class WarningsDrainTest(PollerTestCase):
    """2.5: leaving a (run, period) must fetch its last few seconds of
    warnings once more before the poller stops following it."""

    def test_drain_on_transition_to_idle(self):
        client = FakeClient()
        client.warnings_by[('20261112', 3)] = [{'t': 10.0, 'message': 'last warning'}]
        poller = Poller(client, FakeState())

        run_async(poller._on_status_success(make_status('running', run='20261112', period=3)))
        run_async(poller._on_status_success(make_status('idle')))

        self.assertIn(('20261112', 3, None), client.warnings_calls)
        self.assertEqual(poller.state.recent_warnings, [{'t': 10.0, 'message': 'last warning'}])


class ProgressClearTest(PollerTestCase):
    """The last progress must not stay on the dashboard once the DAQ stops."""

    def test_progress_cleared_when_idle(self):
        state = FakeState()
        poller = Poller(FakeClient(), state)
        state.progress = {'file_id': 3, 'boards': {'A': {'events': 1000}}}

        run_async(poller._on_status_success(make_status('running', run='20261112', period=3)))
        self.assertIsNotNone(state.progress)
        run_async(poller._on_status_success(make_status('idle')))
        self.assertIsNone(state.progress)

    def test_progress_kept_while_a_soft_stop_waits_for_the_file(self):
        state = FakeState()
        poller = Poller(FakeClient(), state)
        state.progress = {'file_id': 3, 'boards': {'A': {'events': 400}}}
        status = make_status('stopping', run='20261112', period=3)
        status['daq']['stop_mode'] = 'soft'

        run_async(poller._on_status_success(status))
        self.assertIsNotNone(state.progress)


if __name__ == '__main__':
    unittest.main()
