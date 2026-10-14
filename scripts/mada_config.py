#!/usr/bin/env python3

"""Read access to MADA_config.json. Every other script gets boards, modules
and flags through here instead of parsing the file itself."""

import json
import os

from mada_errors import MadaError


class ConfigError(MadaError):
    """Raised when the config file is missing, malformed or incomplete."""


def load_config(config_path):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"config file '{config_path}' not found")
    except (OSError, ValueError) as e:
        raise ConfigError(f"cannot read config file '{config_path}': {e}")

    if not isinstance(config, dict) or not isinstance(config.get('gigaIwaki'), dict):
        raise ConfigError(f"config file '{config_path}' has no 'gigaIwaki' section")
    return config


def active_boards(config):
    """[(board name, IP)] of the boards with active == 1, in config order."""
    boards = []
    for name, data in config['gigaIwaki'].items():
        if data.get('active') != 1:
            continue
        if not data.get('IP'):
            raise ConfigError(f"board {name} is active but has no IP")
        boards.append((name, data['IP']))
    return boards


def board_entry_by_ip(config, ip):
    """The config entry of the board with this IP, or None."""
    for data in config['gigaIwaki'].values():
        if data.get('IP') == ip:
            return data
    return None


def module_boards(config):
    """{MPOD module: [(board name, IP)]} for the active boards that have a module."""
    modules = {}
    for name, data in config['gigaIwaki'].items():
        if data.get('active') != 1 or data.get('module') is None:
            continue
        modules.setdefault(data['module'], []).append((name, data['IP']))
    return modules


def latch_up_detect_enabled(config):
    return config.get('general', {}).get('latch_up_detect', 0) == 1


def validate_boards(config):
    """Check what a DAQ run needs from the active boards; raises ConfigError
    listing every problem found."""
    problems = []

    boards = active_boards(config)
    if not boards:
        problems.append('no board has active == 1')

    for name, _ in boards:
        data = config['gigaIwaki'][name]
        for key in ('Vth', 'bias'):
            if not isinstance(data.get(key), (int, float)):
                problems.append(f'{name}: {key} is missing or not a number')
        dac = data.get('DACfile')
        if not dac or not os.path.isfile(dac):
            problems.append(f'{name}: DACfile {dac!r} does not exist')

    if problems:
        raise ConfigError('invalid board settings: ' + '; '.join(problems))
