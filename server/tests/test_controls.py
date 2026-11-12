#!/usr/bin/env python3

"""Tests of the rules for which operations are accepted (mada_server_controls)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mada_server_controls import controls, force_stop_refusal, soft_stop_refusal, start_refusal


def status(phase='running', file_started_at=100.0, file_id=3, stop_mode=None, blocked_by=None):
    return {'phase': phase, 'blocked_by': blocked_by,
            'daq': {'file_id': file_id, 'file_started_at': file_started_at, 'stop_mode': stop_mode}}


def progress(events=400, event_num=1000, file_id=3):
    return {'file_id': file_id, 'event_num': event_num, 'boards': {'A': {'events': events}, 'B': {'events': events}}}


class ForceStopTest(unittest.TestCase):
    def test_allowed_while_acquiring(self):
        self.assertIsNone(force_stop_refusal(status(), progress()))

    def test_refused_while_the_file_is_set_up(self):
        refusal = force_stop_refusal(status(file_started_at=None), progress())
        self.assertEqual(refusal[0], 'busy_file_update')

    def test_refused_when_the_file_is_complete(self):
        refusal = force_stop_refusal(status(), progress(events=1000))
        self.assertEqual(refusal[0], 'busy_file_update')

    def test_refused_when_the_progress_is_cleared(self):
        # mada.py clears the progress when it lowers DAQ enable at the end of a file
        refusal = force_stop_refusal(status(), {'file_id': None, 'boards': {}})
        self.assertEqual(refusal[0], 'busy_file_update')
        self.assertEqual(force_stop_refusal(status(), None)[0], 'busy_file_update')

    def test_refused_when_the_progress_is_of_another_file(self):
        self.assertEqual(force_stop_refusal(status(file_id=4), progress(file_id=3))[0], 'busy_file_update')

    def test_refused_when_not_running(self):
        for phase in ('idle', 'starting', 'stopping'):
            self.assertEqual(force_stop_refusal(status(phase=phase), progress())[0], 'not_running')

    def test_allowed_to_escalate_a_pending_soft_stop(self):
        self.assertIsNone(force_stop_refusal(status(phase='stopping', stop_mode='soft'), progress()))

    def test_refused_without_a_connection(self):
        self.assertEqual(force_stop_refusal(None, None)[0], 'unknown')


class SoftStopTest(unittest.TestCase):
    def test_allowed_at_any_point_of_a_running_daq(self):
        self.assertIsNone(soft_stop_refusal(status(file_started_at=None)))

    def test_refused_when_not_running(self):
        self.assertEqual(soft_stop_refusal(status(phase='idle'))[0], 'not_running')
        self.assertEqual(soft_stop_refusal(status(phase='stopping', stop_mode='soft'))[0], 'not_running')


class StartTest(unittest.TestCase):
    def test_only_when_idle_and_not_blocked(self):
        self.assertIsNone(start_refusal(status(phase='idle')))
        self.assertEqual(start_refusal(status(phase='running'))[0], 'busy')
        self.assertEqual(start_refusal(status(phase='idle', blocked_by='mada_scan'))[0], 'busy')


class ControlsTest(unittest.TestCase):
    def test_flags(self):
        c = controls(status(), progress())
        self.assertFalse(c['start']['enabled'])
        self.assertTrue(c['soft_stop']['enabled'])
        self.assertTrue(c['force_stop']['enabled'])
        c = controls(status(file_started_at=None), progress())
        self.assertTrue(c['soft_stop']['enabled'])
        self.assertFalse(c['force_stop']['enabled'])
        self.assertTrue(c['force_stop']['reason'])


if __name__ == '__main__':
    unittest.main()
