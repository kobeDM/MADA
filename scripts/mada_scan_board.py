#!/usr/bin/env python3

"""The DAC/Vth correction of one board: a DAC scan at the working Vth gives
the DAC of every channel, a second DAC scan at a shifted Vth measures the Vth
counts per DAC count, and Vth scans verify and refine the result until no
DAC value changes any more. Channels that are dead or always hit are not
fitted and keep the DAC of the reference file."""

import json
import os
import shutil
import statistics
from dataclasses import dataclass

import mada_scan_tools as tools
from mada_scan_tools import ScanError

VTH_MAX = 16383
DAC_MAX = 63
DAC_POINTS = DAC_MAX + 1
SLOPE_RANGE = (10.0, 200.0)  # plausible Vth counts per DAC count


@dataclass
class ScanParams:
    events: int = 500          # events per point of the DAC scans
    point_timeout: float = 15  # sec per scan point
    settle: float = 1.0        # sec between a setting and the first data
    slope_dv: int = 200        # Vth shift of the second DAC scan
    window_hit: int = 300      # the Vth scan reaches this far from the working Vth towards the hits
    window_nohit: int = 300    # ... and this far towards the no-hit side
    level: float = 0.005       # channels are aligned where the noise has risen to this fraction of the transition
    dac_level: float = 0.05    # the same for the DAC scans, which have fewer events and only give the start
    metric: str = 'occupancy'  # 'occupancy': events with a hit, 'rate': clocks with a hit
    vth_events: int = 0        # events per point of the Vth scans (0: as events)
    vth_step: int = 10
    max_iter: int = 5          # refinements after the first Vth scan
    target: str = 'config'     # 'config': the working Vth, 'median': the median of the channels
    default_slope: float = 52.0  # Vth counts per DAC count when the measurement fails


def _vth_points(params):
    return (params.window_hit + params.window_nohit) // params.vth_step + 1


def _dac_scan(ip, vth, outdir, params, log, progress, label):
    progress.begin(label, DAC_POINTS)
    tools.acquire(ip, 'dac', outdir, 0, DAC_MAX, 1, ['-v', vth], params.events, params.point_timeout, params.settle, log, progress.update)
    progress.end()
    return tools.fit(outdir, 'dac', log, level=params.dac_level, metric=params.metric)


def _vth_scan(ip, vth0, dac_file, outdir, params, log, progress, label, hits_low):
    near, far = (params.window_nohit, params.window_hit) if not hits_low else (params.window_hit, params.window_nohit)
    low = max(0, vth0 - near)
    high = min(VTH_MAX, vth0 + far)
    progress.begin(label, _vth_points(params))
    events = params.vth_events or params.events
    tools.acquire(ip, 'vth', outdir, low, high, params.vth_step, ['-d', dac_file], events, params.point_timeout, params.settle, log, progress.update)
    progress.end()
    return tools.fit(outdir, 'vth', log, target=vth0, level=params.level, metric=params.metric)


def _measure_slope(fit0, vth0, fit1, vth1, params, log, warnings):
    try:
        slope = float(tools.measure_slope(fit0, vth0, fit1, vth1, log)['slope'])
    except ScanError as e:
        warnings.append(f'slope measurement failed ({e}); using {params.default_slope}')
        return params.default_slope

    if not SLOPE_RANGE[0] <= slope <= SLOPE_RANGE[1]:
        warnings.append(f'measured slope {slope:.1f} Vth/DAC is outside {SLOPE_RANGE}; using {params.default_slope}')
        return params.default_slope
    return slope


def _hits_at_low_vth(dac_scan_dir, slope):
    """Which end of the Vth scale has the hits. The DAC scan tells whether the
    hits are at high or low DAC values; with a positive slope (Vth counts per
    DAC count along a constant noise level) hits at high DAC values mean hits at
    low Vth."""
    hits_at_low_dac = tools.dac_polarity(dac_scan_dir) > 0
    return hits_at_low_dac == (slope < 0)


def _spread(fit):
    centers = fit['centers']
    return {
        'ok': len(centers),
        'classes': fit['classes'],
        'median': statistics.median(centers) if centers else None,
        'rms': statistics.pstdev(centers) if len(centers) > 1 else None,
    }


def _refine_loop(ip, vth0, dac_file, slope, hits_low, outdir, params, log, progress, warnings):
    """Vth scans with refinements; returns (final DAC file, iteration records, last fit)."""
    records = []
    for it in range(params.max_iter + 1):
        progress.say(f'Vth scan {it} (DAC file {os.path.basename(dac_file)})...')
        fit = _vth_scan(ip, vth0, dac_file, f'{outdir}/vth_scan_{it}', params, log, progress, f'Vth scan {it}', hits_low)
        record = _spread(fit)
        record['dac_file'] = dac_file
        records.append(record)
        progress.say(f"  aligned positions: median {record['median']}, rms {record['rms']}, classes {record['classes']}")
        if it == params.max_iter:
            break

        target = vth0 if params.target == 'config' else 'median'
        new_dac = f'{outdir}/dac_{it + 1}.dac'
        result = tools.refine_dac(f'{outdir}/vth_scan_{it}/fit_result.csv', dac_file, slope, new_dac, target, log)
        record['refine'] = result
        progress.say(f"  refine: {result['changed']} channels changed, {result['clamped']} clamped, "
                     f"offset rms {result['offset_rms_dac_before']} -> {result['offset_rms_dac_after']} DAC")
        if int(result['clamped']):
            warnings.append(f"{result['clamped']} channels cannot reach the target within DAC 0-63")
        if int(result['changed']) == 0:
            break
        dac_file = new_dac
    return dac_file, records, fit


def scan_board(name, ip, vth0, reference_dac, outdir, params, progress):
    """Returns the summary of one board; raises ScanError when a scan fails.
    progress is the BoardProgress of the board."""
    os.makedirs(outdir, exist_ok=True)
    log = outdir + '/scan.log'
    warnings = []
    progress.plan(2 * DAC_POINTS + _vth_points(params) * (params.max_iter + 1))

    progress.say(f'DAC scan at Vth {vth0}...')
    dac_fit0 = _dac_scan(ip, vth0, outdir + '/dac_scan_0', params, log, progress, 'DAC scan 0')
    progress.say(f"  classes {dac_fit0['classes']}")
    dac_file = outdir + '/dac_0.dac'
    base = tools.correct_dac(outdir + '/dac_scan_0/fit_result.csv', reference_dac, dac_file, log)

    vth1 = min(VTH_MAX, vth0 + params.slope_dv)
    progress.say(f'DAC scan at Vth {vth1} (slope)...')
    _dac_scan(ip, vth1, outdir + '/dac_scan_1', params, log, progress, 'DAC scan 1')
    slope = _measure_slope(outdir + '/dac_scan_0/fit_result.csv', vth0, outdir + '/dac_scan_1/fit_result.csv', vth1, params, log, warnings)
    hits_low = _hits_at_low_vth(outdir + '/dac_scan_0', slope)
    progress.say(f"  slope {slope:.1f} Vth counts per DAC; the hits are at {'low' if hits_low else 'high'} Vth")

    final, records, last_fit = _refine_loop(ip, vth0, dac_file, slope, hits_low, outdir, params, log, progress, warnings)
    shutil.copy(final, outdir + '/final.dac')

    unfitted = {ch: cls for ch, cls in last_fit['by_channel'].items() if cls != 'ok'}
    summary = {
        'board': name, 'ip': ip, 'vth': vth0, 'level': params.level, 'metric': params.metric, 'slope': slope,
        'hits_at_low_vth': hits_low, 'final_dac': outdir + '/final.dac',
        'dac_scan': {'classes': dac_fit0['classes'], 'dac_median': base.get('dac_median'), 'dac_rms': base.get('dac_rms')},
        'iterations': records, 'unfitted_channels': unfitted, 'warnings': warnings,
    }
    with open(outdir + '/summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    return summary
