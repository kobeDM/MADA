#!/usr/bin/env python3

"""Live per-board event counts while a file is being acquired."""

import sys
import time

from mada_gigaiwaki import GigaIwakiError

UPIC_FOOTER = b'uPIC'
POLL_INTERVAL = 0.2  # sec


class ProgressMonitor:
    """Tracks and displays each board's live event count during acquisition,
    by tailing the growing .mada files for the 'uPIC' footer marker."""

    def __init__(self, mada_files, event_num, poll_interval=POLL_INTERVAL):
        self.mada_files = mada_files
        self.event_num = event_num
        self.poll_interval = poll_interval

        self.board_ids = list(mada_files.keys())
        self.offsets = {board_id: 0 for board_id in self.board_ids}
        self.carries = {board_id: b'' for board_id in self.board_ids}
        self.counts = {board_id: 0 for board_id in self.board_ids}
        self.is_tty = sys.stdout.isatty()
        self._drawn = False

    @staticmethod
    def _count_new_footers(data, carry):
        # Prepend the tail of the previous chunk so a footer split across
        # two polls (e.g. "...uPI" | "C...") is still detected.
        buf = carry + data
        return buf.count(UPIC_FOOTER), buf[-(len(UPIC_FOOTER) - 1):]

    def poll(self):
        for board_id, path in self.mada_files.items():
            try:
                with open(path, 'rb') as f:
                    f.seek(self.offsets[board_id])
                    chunk = f.read()
            except FileNotFoundError:
                continue

            if not chunk:
                continue

            found, self.carries[board_id] = self._count_new_footers(chunk, self.carries[board_id])
            self.counts[board_id] += found
            self.offsets[board_id] += len(chunk)

    def render(self, final=False):
        # On a TTY, redraw the same lines in place every poll (cheap, bounded
        # size). Off a TTY (redirected to a file, e.g. --daemon), each poll
        # would otherwise append a fresh line and blow up the log file, so
        # only print once the counts are final.
        if self.is_tty:
            if self._drawn:
                sys.stdout.write(f'\x1b[{len(self.board_ids)}A')
            for board_id in self.board_ids:
                line = f'  {board_id}: {self.counts[board_id]:>6}/{self.event_num:<6} events stored'
                sys.stdout.write('\x1b[2K' + line + '\n')
            sys.stdout.flush()
            self._drawn = True
        elif final:
            for board_id in self.board_ids:
                line = f'  {board_id}: {self.counts[board_id]:>6}/{self.event_num:<6} events stored'
                print(line)
            sys.stdout.flush()

    def wait_for_any_exit(self, procs, on_poll=None):
        """Poll and render while waiting for at least one gigaiwaki process
        to exit (matching the intended 'one board done -> stop all' policy).
        Raises GigaIwakiError if any process exited with a non-zero status
        (e.g. MadaIwaki lost its connection to the board). on_poll, if given,
        is called every poll and may raise to stop the wait."""
        print('Waiting for gigaiwaki processes to finish...')
        process_num_org = len(procs)

        while True:
            self.poll()
            self.render()
            if on_poll:
                on_poll()

            alive = [p for p in procs.values() if p.poll() is None]
            if len(alive) != process_num_org:
                break
            time.sleep(self.poll_interval)

        # Catch any events written just before the processes were found to
        # have stopped, and print the final per-board counts.
        self.poll()
        self.render(final=True)

        for board_id, proc in procs.items():
            if proc.poll() is not None and proc.returncode != 0:
                raise GigaIwakiError(
                    f'gigaiwaki for {board_id} exited with error (code {proc.returncode})'
                )
