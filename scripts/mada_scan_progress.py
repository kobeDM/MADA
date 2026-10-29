#!/usr/bin/env python3

"""Live progress of a scan session: one bar per board with the stage, the
scan points done, the elapsed time and an estimate of the time left. On a
terminal the bars are redrawn in place; in a log file one status line per
board is written every STATUS_INTERVAL seconds instead."""

import sys
import threading
import time

REDRAW_INTERVAL = 1.0   # sec between redraws on a terminal
STATUS_INTERVAL = 60.0  # sec between status lines off a terminal
BAR_WIDTH = 24
MIN_FRACTION = 0.03     # no estimate of the time left before this much is done


def format_time(seconds):
    seconds = int(max(seconds, 0))
    hours, rest = divmod(seconds, 3600)
    return f'{hours}:{rest // 60:02d}:{rest % 60:02d}' if hours else f'{rest // 60}:{rest % 60:02d}'


class _Board:
    def __init__(self, name):
        self.name = name
        self.planned = 0       # scan points of the whole job
        self.completed = 0     # points of the finished stages
        self.stage = 'waiting'
        self.stage_total = 0
        self.stage_done = 0
        self.finished = False
        self.failed = False
        self.started = time.time()
        self.last_status = 0.0

    def fraction(self):
        if self.finished:
            return 1.0
        if self.planned <= 0:
            return 0.0
        return min((self.completed + self.stage_done) / self.planned, 1.0)

    def line(self):
        fraction = self.fraction()
        filled = int(round(BAR_WIDTH * fraction))
        elapsed = time.time() - self.started
        if self.failed:
            tail = 'FAILED'
        elif self.finished:
            tail = f'done in {format_time(elapsed)}'
        else:
            eta = f'ETA {format_time(elapsed / fraction * (1 - fraction))}' if fraction >= MIN_FRACTION else 'ETA --'
            tail = f'{format_time(elapsed)} {eta}'
        stage = f'{self.stage} {self.stage_done}/{self.stage_total}' if self.stage_total else ('' if self.finished else self.stage)
        return f"[{self.name}] [{'#' * filled}{'-' * (BAR_WIDTH - filled)}] {fraction * 100:3.0f}%  {stage}  {tail}"


class ScanProgress:
    """Shared by the board threads; every method is thread-safe."""

    def __init__(self, names, stream=None):
        self.stream = stream or sys.stdout
        self.tty = self.stream.isatty()
        self.boards = {name: _Board(name) for name in names}
        self._lock = threading.Lock()
        self._drawn = 0
        self._stop = threading.Event()
        self._thread = None

    def board(self, name):
        return BoardProgress(self, self.boards[name])

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        with self._lock:
            self._erase()
            for board in self.boards.values():
                self._write(board.line() + '\n')

    def _write(self, text):
        self.stream.write(text)
        self.stream.flush()

    def _erase(self):
        if self.tty and self._drawn:
            self._write(f'\x1b[{self._drawn}A' + '\x1b[J')
        self._drawn = 0

    def _draw(self):
        if not self.tty:
            return
        for board in self.boards.values():
            self._write('\x1b[2K' + board.line() + '\n')
        self._drawn = len(self.boards)

    def _loop(self):
        while not self._stop.wait(REDRAW_INTERVAL if self.tty else 5.0):
            with self._lock:
                if self.tty:
                    self._erase()
                    self._draw()
                else:
                    now = time.time()
                    for board in self.boards.values():
                        if not board.finished and now - board.last_status >= STATUS_INTERVAL:
                            board.last_status = now
                            self._write(board.line() + '\n')

    def message(self, board, text):
        """Print an event line above the bars."""
        with self._lock:
            self._erase()
            self._write(f'[{board.name}] {text}\n')
            self._draw()


class BoardProgress:
    """The view of one board, used by the thread that scans it."""

    def __init__(self, owner, board):
        self._owner = owner
        self._board = board

    def say(self, text):
        self._owner.message(self._board, text)

    def plan(self, total_points):
        with self._owner._lock:
            self._board.planned = total_points

    def begin(self, stage, total):
        with self._owner._lock:
            self._board.stage = stage
            self._board.stage_total = total
            self._board.stage_done = 0

    def update(self, done):
        with self._owner._lock:
            self._board.stage_done = min(done, self._board.stage_total) if self._board.stage_total else done

    def end(self):
        with self._owner._lock:
            self._board.completed += self._board.stage_total
            self._board.stage_done = 0

    def finish(self, failed=False):
        with self._owner._lock:
            self._board.finished = not failed
            self._board.failed = failed
            self._board.stage = 'failed' if failed else 'done'
            self._board.stage_total = 0
