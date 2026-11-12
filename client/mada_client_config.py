"""Settings of the DAQ client (config/MADA_client.json)."""

import json
import os
import re
import stat

RUN_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')

DEFAULTS = {
    'listen_host': '0.0.0.0',
    'port': 8765,
    'carry_over_config': True,
    'defaults': {'file_num': 512, 'event_num': 1000},
    'limits': {'file_num_max': 10000, 'event_num_max': 100000},
}
REQUIRED = ('allowed_servers', 'token_file', 'data_root')


class ClientConfigError(Exception):
    pass


class Settings:
    def __init__(self, raw, token):
        self.listen_host = raw['listen_host']
        self.port = raw['port']
        self.allowed_servers = list(raw['allowed_servers'])
        self.token = token
        self.data_root = os.path.realpath(raw['data_root'])
        self.carry_over_config = raw['carry_over_config']
        self.file_num_default = raw['defaults']['file_num']
        self.event_num_default = raw['defaults']['event_num']
        self.file_num_max = raw['limits']['file_num_max']
        self.event_num_max = raw['limits']['event_num_max']
        self.simulate = False
        self.sim_env = {}


def _merge(raw):
    merged = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    for key, value in raw.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def _read_token(path, problems):
    try:
        mode = os.stat(path).st_mode
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            problems.append(f'token_file {path} must not be accessible by group/others (chmod 600)')
        with open(path) as f:
            token = f.read().strip()
    except OSError as e:
        problems.append(f'cannot read token_file {path}: {e}')
        return None
    if not token:
        problems.append(f'token_file {path} is empty')
    return token


def _check(raw, problems):
    known = set(DEFAULTS) | set(REQUIRED)
    problems += [f'unknown key {key!r}' for key in raw if key not in known and not key.startswith('_')]
    problems += [f'{key} is missing' for key in REQUIRED if key not in raw]
    if not isinstance(raw.get('allowed_servers'), list) or not raw.get('allowed_servers'):
        problems.append('allowed_servers must be a non-empty list of IP addresses')
    if not os.path.isdir(str(raw.get('data_root'))):
        problems.append(f"data_root {raw.get('data_root')!r} is not a directory")
    for key, value in (('port', raw.get('port')),
                       ('defaults.file_num', raw['defaults'].get('file_num')),
                       ('defaults.event_num', raw['defaults'].get('event_num')),
                       ('limits.file_num_max', raw['limits'].get('file_num_max')),
                       ('limits.event_num_max', raw['limits'].get('event_num_max'))):
        if not isinstance(value, int) or value < 1:
            problems.append(f'{key} must be a positive integer')


def load_settings(path):
    """Settings from the JSON file; raises ClientConfigError listing every problem."""
    try:
        with open(path) as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        raise ClientConfigError(f'cannot read {path}: {e}')
    if not isinstance(raw, dict):
        raise ClientConfigError(f'{path} is not a JSON object')

    raw = _merge(raw)
    problems = []
    _check(raw, problems)
    token = _read_token(raw.get('token_file', ''), problems)
    if problems:
        raise ClientConfigError('invalid client settings: ' + '; '.join(problems))
    return Settings(raw, token)
