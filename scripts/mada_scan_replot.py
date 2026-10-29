#!/usr/bin/env python3

"""Redo the fits and plots of finished scans from their saved data (no
board access). Use it after the plotting or the fit of ScanFit changed."""

import argparse
import glob
import json
import os
import sys

import mada_scan_tools as tools
from mada_errors import MadaError


def replot_board(board_dir, level=None, metric=None):
    """level: the alignment level; default the one the scan was made with
    (0.5, the center, for scans of before the level existed)."""
    with open(board_dir + '/summary.json') as f:
        summary = json.load(f)
    vth = summary['vth']
    level = summary.get('level', 0.5) if level is None else level
    metric = summary.get('metric', 'rate') if metric is None else metric
    log = board_dir + '/scan.log'

    for path in sorted(glob.glob(board_dir + '/dac_scan_*')):
        print(f'ScanFit {path} (level {level}, {metric})')
        tools.fit(path, 'dac', log, level=level, metric=metric)
    for path in sorted(glob.glob(board_dir + '/vth_scan_*')):
        print(f'ScanFit {path} (target {vth}, level {level}, {metric})')
        tools.fit(path, 'vth', log, target=vth, level=level, metric=metric)


def main():
    parser = argparse.ArgumentParser(description='Redo the fits and plots of finished scans (scan_runNNNN directories).')
    parser.add_argument('runs', nargs='+', help='scan_runNNNN directories')
    parser.add_argument('--level', type=float, help='alignment level (default: the one of the scan)')
    parser.add_argument('--metric', choices=['occupancy', 'rate'], help='what the level counts (default: the one of the scan)')
    args = parser.parse_args()

    failed = 0
    for run in args.runs:
        for summary in sorted(glob.glob(run + '/*/summary.json')):
            try:
                replot_board(os.path.dirname(summary), args.level, args.metric)
            except (MadaError, OSError, KeyError, ValueError) as e:
                failed += 1
                print(f'ERROR: {summary}: {e}')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
