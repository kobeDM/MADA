#!/usr/bin/env python3

"""Read access to the daq-server config (config/MADA_server_SKEL.json is the
template). Every other module gets settings through here instead of parsing
the file itself. See docs/specs/2026-11-12_3.md section 6 and
docs/specs/2026-11-12.md for the contract this server implements.

Login users live in this config file (`users`), not in the DB -- modeled on
/home/msgc/repo/MPOD/web_backend/app/config.py and create_user.py: a login is
an OS-level operation (editing a file on this machine), kept separate from
the DB that holds the server's own runtime state (operations, notifications)."""

import json
import os
import stat

import bcrypt


class ConfigError(RuntimeError):
    """Raised when the config file (or a file it points to) is missing,
    malformed or incomplete."""


DEFAULTS = {
    'listen_host': '0.0.0.0',
    'port': 8080,
    'cookie_secure': False,
    'presets': [],
    'users': {},
}


def _require_mode_600(path, label):
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except OSError as e:
        raise ConfigError(f"cannot stat {label} '{path}': {e}")
    if mode != 0o600:
        raise ConfigError(f"{label} '{path}' must be mode 600 (found {oct(mode)})")


def load_config(config_path):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"config file '{config_path}' not found")
    except (OSError, ValueError) as e:
        raise ConfigError(f"cannot read config file '{config_path}': {e}")

    if not isinstance(config, dict):
        raise ConfigError(f"config file '{config_path}' is not a JSON object")

    merged = dict(DEFAULTS)
    merged.update(config)
    _validate(merged, config_path)
    return merged


def _validate(config, config_path):
    problems = []

    client = config.get('client')
    if not isinstance(client, dict):
        problems.append("'client' section is missing")
        client = {}
    if not client.get('base_url'):
        problems.append("'client.base_url' is missing")
    if not client.get('token_file'):
        problems.append("'client.token_file' is missing")
    if 'timeout' in client and not isinstance(client['timeout'], (int, float)):
        problems.append("'client.timeout' must be a number")

    if not config.get('state_dir'):
        problems.append("'state_dir' is missing")

    if not config.get('session_secret'):
        problems.append("'session_secret' is missing (python3 -c \"import secrets; print(secrets.token_hex(32))\")")

    users = config.get('users', {})
    if not isinstance(users, dict):
        problems.append("'users' must be an object")
    else:
        for name, entry in users.items():
            if not isinstance(entry, dict) or not entry.get('password_hash') \
                    or entry.get('role') not in ('viewer', 'operator'):
                problems.append(f"users.{name} needs a 'password_hash' and a 'role' of 'viewer' or 'operator'")

    if not isinstance(config.get('port'), int) or not (1 <= config['port'] <= 65535):
        problems.append("'port' must be an integer 1-65535")

    presets = config.get('presets', [])
    if not isinstance(presets, list):
        problems.append("'presets' must be a list")
    else:
        for i, preset in enumerate(presets):
            if not isinstance(preset, dict) or not preset.get('name') or \
                    not isinstance(preset.get('event_num'), int):
                problems.append(f"presets[{i}] needs a 'name' and an integer 'event_num'")

    if problems:
        raise ConfigError(f"invalid config '{config_path}': " + '; '.join(problems))

    _require_mode_600(client['token_file'], 'client token file')


def read_client_token(config):
    with open(config['client']['token_file'], 'r') as f:
        return f.read().strip()


def client_timeout(config):
    return config['client'].get('timeout', 5.0)


def state_dir(config):
    path = config['state_dir']
    os.makedirs(path, exist_ok=True)
    return path


def db_path(config):
    return os.path.join(state_dir(config), 'mada_server.db')


def pidfile_path(config):
    return os.path.join(state_dir(config), 'mada_server.pid')


def log_path(config):
    return os.path.join(state_dir(config), 'mada_server.log')


# -- login users (stored in the config file itself; CLI-only, see mada_server.py) --

def _load_raw(path):
    with open(path, 'r') as f:
        return json.load(f)


def _save_raw(data, path):
    """Write back to the same file atomically (temp + rename), as
    MPOD's config.save_config does, so a crash mid-write can't corrupt it."""
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write('\n')
    os.replace(tmp_path, path)


def add_user(path, username, password, role):
    data = _load_raw(path)
    users = data.setdefault('users', {})
    if username in users:
        raise ConfigError(f"user '{username}' already exists")
    users[username] = {
        'password_hash': bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('ascii'),
        'role': role,
    }
    _save_raw(data, path)


def set_password(path, username, password):
    data = _load_raw(path)
    users = data.get('users', {})
    if username not in users:
        raise ConfigError(f"no such user '{username}'")
    users[username]['password_hash'] = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('ascii')
    _save_raw(data, path)


def remove_user(path, username):
    data = _load_raw(path)
    users = data.get('users', {})
    if username not in users:
        raise ConfigError(f"no such user '{username}'")
    del users[username]
    _save_raw(data, path)
