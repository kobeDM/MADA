"""Reading the run directories: runs, periods, files, warnings, logs, config."""

import json
import os
import re
import time

import mada_client_paths as paths
from mada_client_config import RUN_PATTERN
from mada_client_errors import ApiError

PERIOD_RE = re.compile(r'^per(\d{4})$')
LOG_RE = re.compile(r'^.+_\d{4}\.log$')
LEVEL_RE = re.compile(r'^([A-Z]+) t=\S+ kind=(\S+)')
RUNS_TTL = 5.0  # sec
LOG_TAIL_BYTES = 8192

_runs_cache = {'time': 0.0, 'root': None, 'value': []}
_info_cache = {}


def clear_cache():
    _runs_cache['time'] = 0.0
    _info_cache.clear()


def run_path(settings, run):
    """Directory of a run; ApiError for a bad name or a missing directory."""
    if not RUN_PATTERN.match(run or ''):
        raise ApiError(422, 'invalid_request', f'invalid run name {run!r}')
    path = os.path.realpath(os.path.join(settings.data_root, run))
    if os.path.dirname(path) != settings.data_root:
        raise ApiError(422, 'invalid_request', f'invalid run name {run!r}')
    if not os.path.isdir(path):
        raise ApiError(404, 'not_found', f'run {run} not found')
    return path


def period_numbers(run_dir):
    numbers = []
    try:
        for entry in os.scandir(run_dir):
            match = PERIOD_RE.match(entry.name)
            if match and entry.is_dir():
                numbers.append(int(match.group(1)))
    except OSError:
        pass
    return sorted(numbers)


def list_runs(settings, use_cache=True):
    """Runs (directories with perNNNN) under data_root, newest first."""
    now = time.time()
    if use_cache and _runs_cache['root'] == settings.data_root and now - _runs_cache['time'] < RUNS_TTL:
        return _runs_cache['value']

    runs = []
    for entry in os.scandir(settings.data_root):
        if not entry.is_dir() or not RUN_PATTERN.match(entry.name):
            continue
        periods = period_numbers(entry.path)
        if not periods:
            continue
        modified = max(os.stat(f'{entry.path}/per{p:04d}').st_mtime for p in periods)
        runs.append({'run': entry.name, 'periods': periods,
                     'has_config': os.path.isfile(entry.path + '/MADA_config.json'),
                     'modified': modified})
    runs.sort(key=lambda r: r['modified'], reverse=True)
    _runs_cache.update(time=now, root=settings.data_root, value=runs)
    return runs


def latest_run(settings):
    runs = list_runs(settings)
    return runs[0]['run'] if runs else None


def period_path(settings, run, period):
    path = f'{run_path(settings, run)}/per{period:04d}'
    if not os.path.isdir(path):
        raise ApiError(404, 'not_found', f'period {period} of run {run} not found')
    return path


def read_config(settings, run):
    path = run_path(settings, run) + '/MADA_config.json'
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise ApiError(404, 'not_found', f'run {run} has no MADA_config.json')
    except ValueError as e:
        raise ApiError(500, 'internal', f'{path} is not valid JSON ({e})')


def _read_info(path):
    key = (path, os.stat(path).st_mtime_ns)
    if key not in _info_cache:
        try:
            with open(path, encoding='utf-8') as f:
                _info_cache[key] = json.load(f)
        except (OSError, ValueError):
            _info_cache[key] = None
    return _info_cache[key]


def _file_entry(file_id, board_infos):
    entry = {'file_id': file_id, 'valid': True, 'invalid_reason': None,
             'start': None, 'end': None, 'boards': {}}
    starts, ends = [], []
    for board_id, info in sorted(board_infos.items()):
        runinfo = info.get('runinfo', {})
        if runinfo.get('valid') is False:
            entry['valid'] = False
            entry['invalid_reason'] = entry['invalid_reason'] or runinfo.get('invalid_reason')
        starts.append(runinfo.get('start'))
        ends.append(runinfo.get('end'))
        size = runinfo.get('size')
        entry['boards'][board_id] = {'size': int(size) if size is not None else None}
    starts = [s for s in starts if s is not None]
    entry['start'] = min(starts) if starts else None
    entry['end'] = max(ends) if ends and None not in ends else None
    return entry


def read_files(period_dir, after=-1, limit=100):
    """File entries of a period (from the .info files), ordered by file number."""
    by_file = {}
    for name in os.listdir(period_dir):
        if not name.endswith('.info'):
            continue
        board_id, _, number = name[:-len('.info')].rpartition('_')
        if not board_id or not number.isdigit() or int(number) <= after:
            continue
        info = _read_info(f'{period_dir}/{name}')
        if info is not None:
            by_file.setdefault(int(number), {})[board_id] = info
    return [_file_entry(n, by_file[n]) for n in sorted(by_file)[:limit]]


def parse_warning(line):
    parts = line.rstrip('\n').split('\t', 4)
    if len(parts) < 5:
        return None
    try:
        t, file_id = float(parts[0]), int(parts[2])
    except ValueError:
        return None
    match = LEVEL_RE.match(parts[4])
    return {'t': t, 'time': parts[1], 'file_id': file_id, 'source': parts[3],
            'level': match.group(1) if match else None,
            'kind': match.group(2) if match else None, 'message': parts[4]}


def read_warnings(period_dir, after=0.0, limit=200):
    records = []
    try:
        with open(period_dir + '/warnings.log', encoding='utf-8', errors='replace') as f:
            for line in f:
                if not line.endswith('\n'):
                    break
                record = parse_warning(line)
                if record and record['t'] > after:
                    records.append(record)
                    if len(records) >= limit:
                        break
    except FileNotFoundError:
        pass
    return records


def newest_log():
    """Newest daemon log (<run>_<period>.log) under $MADAHOME/run, or None."""
    best = None
    try:
        for entry in os.scandir(paths.RUN_DIR):
            if LOG_RE.match(entry.name):
                if best is None or entry.stat().st_mtime > best[0]:
                    best = (entry.stat().st_mtime, entry.name)
    except OSError:
        pass
    return best[1] if best else None


def _complete_utf8(data):
    """data without a trailing partial UTF-8 character."""
    for cut in range(0, 4):
        try:
            data[:len(data) - cut].decode('utf-8')
            return data[:len(data) - cut]
        except UnicodeDecodeError:
            continue
    return data


def read_log(name, offset=None, max_bytes=65536):
    if name is None:
        return {'file': None, 'offset': 0, 'size': 0, 'text': ''}
    path = f'{paths.RUN_DIR}/{name}'
    try:
        size = os.path.getsize(path)
        if offset is None:
            offset = max(0, size - LOG_TAIL_BYTES)
        elif offset > size:
            offset = 0
        with open(path, 'rb') as f:
            f.seek(offset)
            data = _complete_utf8(f.read(max_bytes))
    except FileNotFoundError:
        return {'file': name, 'offset': 0, 'size': 0, 'text': ''}
    return {'file': name, 'offset': offset + len(data), 'size': size,
            'text': data.decode('utf-8', errors='replace')}
