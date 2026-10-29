#!/usr/bin/env python3

import argparse
import sys

from mada_errors import MadaError
from mada_scan_board import ScanParams
from mada_scan_session import run_scan

CONFIG = './MADA_config.json'


def arg_parser():
    d = ScanParams()
    parser = argparse.ArgumentParser(description='DAC and Vth correction of the active boards with noise-only scans. '
                                     'Needs the boards powered (mada_encoder_power.py 1) and the external trigger running. '
                                     'Writes <board>.dac files; copy them into the config by hand.')
    parser.add_argument('-c', '--config', default=CONFIG)
    parser.add_argument('-b', '--board', action='append', help='board name or IP to scan (repeatable; default: all active boards)')
    parser.add_argument('-o', '--output', help='output directory (default: the next scan_runNNNN)')
    parser.add_argument('-n', '--events', type=int, default=d.events, help='events per scan point')
    parser.add_argument('-t', '--timeout', type=float, default=d.point_timeout, help='sec per scan point')
    parser.add_argument('-s', '--settle', type=float, default=d.settle, help='sec between a setting and the first data')
    parser.add_argument('--slope-dv', type=int, default=d.slope_dv, help='Vth shift of the second DAC scan')
    parser.add_argument('--level', type=float, default=d.level,
                        help='the channels are aligned at the Vth where the noise has risen to this fraction of the whole noise transition '
                             '(0 to 0.5; 0.5 is the center; a small value is a point where the noise is low)')
    parser.add_argument('--metric', choices=['occupancy', 'rate'], default=d.metric,
                        help='what the level counts: events with a hit (occupancy) or clocks with a hit (rate)')
    parser.add_argument('--vth-events', type=int, default=d.vth_events, help='events per point of the Vth scans (default: --events); the noise tail needs many')
    parser.add_argument('--dac-level', type=float, default=d.dac_level, help='--level for the DAC scans (fewer events, they only give the start)')
    parser.add_argument('--window-hit', type=int, default=d.window_hit, help='Vth scan range towards the hits from the working Vth (the side is found from the DAC scan)')
    parser.add_argument('--window-nohit', type=int, default=d.window_nohit, help='Vth scan range towards the no-hit side from the working Vth')
    parser.add_argument('--step', type=int, default=d.vth_step, help='Vth scan step')
    parser.add_argument('--max-iter', type=int, default=d.max_iter, help='refinements after the first Vth scan')
    parser.add_argument('--target', choices=['config', 'median'], default=d.target,
                        help='Vth the channels are aligned to: the working Vth of the config or the median of the channels')
    return parser.parse_args()


def main():
    print('*** mada_scan.py start ***')
    args = arg_parser()
    params = ScanParams(events=args.events, point_timeout=args.timeout, settle=args.settle, slope_dv=args.slope_dv,
                        window_hit=args.window_hit, window_nohit=args.window_nohit, dac_level=args.dac_level, vth_step=args.step, max_iter=args.max_iter, target=args.target, level=args.level, metric=args.metric, vth_events=args.vth_events)

    try:
        failed = run_scan(args.config, params, names=args.board, outdir=args.output)
    except KeyboardInterrupt:
        print('Keyboard interrupt received. Scan stopped.')
        sys.exit(130)
    except MadaError as e:
        print(f'ERROR: {e}')
        sys.exit(1)

    print('*** mada_scan.py end ***')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
