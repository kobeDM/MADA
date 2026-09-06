#!/usr/bin/env python3

"""Shared rate-log line writer, used by mada.py and mada_daq_killer.py.

Log line format (tab-separated), appended to <rate_root>/YYYYMMDD:
    t  start_time  end_time  size_1 .. size_N  rate_1 .. rate_N

N is the number of active boards for the run; rate_i = size_i / realtime
for the board at the same position i. Callers must pass sizes in a
consistent board order (e.g. the active-board order from MADA_config.json)
since the board identity itself is not encoded in the line.
"""

import datetime


def write_rate_log(rate_root, start_time, end_time, sizes):
    realtime = end_time - start_time
    dt = datetime.datetime.fromtimestamp(end_time)

    t = dt.strftime("%Y/%m/%d/%H:%M:%S")
    rates = [size / realtime for size in sizes]
    out_list = [t, start_time, end_time] + list(sizes) + rates
    out_str = '\t'.join(map(str, out_list)) + '\n'

    rate_file_path = dt.strftime(f"{rate_root}/%Y%m%d")
    with open(rate_file_path, 'a', encoding='utf-8') as f:
        f.write(out_str)
