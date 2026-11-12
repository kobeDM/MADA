#!/usr/bin/env python3

"""The server's view of the DAQ, held in memory (spec 2026-11-12_3.md
section 5: "latest state: in memory; losing it on restart is fine"). mada_server_poller.py
is the only writer; request handlers and the SSE stream only read a
snapshot. Losing this on restart is fine: it is rebuilt from the next poll."""

import asyncio
import time

from mada_server_controls import controls

RECENT_WARNINGS_MAX = 200


class ServerState:
    def __init__(self):
        self.connected = None  # None: not polled yet, True/False after
        self.consecutive_failures = 0
        self.last_error = None
        self.last_success_at = None
        self.status = None
        self.progress = None
        self.recent_warnings = []  # newest last, capped at RECENT_WARNINGS_MAX
        self._subscribers = set()

    def snapshot(self):
        return {
            'connected': self.connected,
            'last_error': self.last_error,
            'last_success_at': self.last_success_at,
            'status': self.status,
            'progress': self.progress,
            'recent_warnings': list(self.recent_warnings[-50:]),
            'controls': controls(self.status if self.connected else None, self.progress),
            'server_time': time.time(),
        }

    def push_warnings(self, records):
        self.recent_warnings.extend(records)
        if len(self.recent_warnings) > RECENT_WARNINGS_MAX:
            self.recent_warnings = self.recent_warnings[-RECENT_WARNINGS_MAX:]

    def subscribe(self):
        """A queue that receives this state's snapshot every time
        broadcast() is called, for one SSE connection."""
        queue = asyncio.Queue(maxsize=4)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue):
        self._subscribers.discard(queue)

    def broadcast(self):
        payload = self.snapshot()
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # a slow viewer misses an update; the next one carries full state


state = ServerState()
