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


SCI_DEFAULTS = {
    'range': 'low',
    'buffer_samples': 8192,
    'pre_trigger_samples': 8000,
    'save_waveform': 0,
}
SCI_MAX_PRE_TRIGGER = 8192  # samples the ADALM can keep before the trigger
SCI_MIN_POST_TRIGGER = 100  # samples after the trigger edge that the buffer must keep
SCI_RANGE_V = {'low': 2.5, 'high': 25.0}


def sci_settings(config):
    """The SCI section with the defaults filled in, or None when there is none."""
    section = config.get('SCI')
    if not isinstance(section, dict):
        return None
    settings = dict(SCI_DEFAULTS)
    settings.update(section)
    return settings


def _check_sci_signal(name, signal, limit, problems):
    if not isinstance(signal, dict):
        problems.append(f'SCI.{name} is missing')
        return
    threshold = signal.get('threshold_V')
    if not isinstance(threshold, (int, float)) or abs(threshold) >= limit:
        problems.append(f'SCI.{name}.threshold_V must be a number within +-{limit} V')
    if signal.get('edge') not in ('rising', 'falling'):
        problems.append(f"SCI.{name}.edge must be 'rising' or 'falling'")


def validate_sci(config):
    """Check what the SCI mode needs; raises ConfigError listing every problem."""
    settings = sci_settings(config)
    if settings is None:
        raise ConfigError("the SCI mode needs a 'SCI' section in the config")

    problems = []
    if settings.get('active') != 1:
        problems.append('SCI.active is not 1')

    serial = settings.get('S/N')
    if not serial:
        problems.append('SCI.S/N is missing')
    daq_serials = {entry.get('S/N') for entry in config.get('ADALM', {}).values() if isinstance(entry, dict)}
    if serial and serial in daq_serials:
        problems.append('SCI.S/N is the same ADALM as one of the DAQ roles (MADALM_n); use another ADALM')

    channels = settings.get('channels', {})
    pmt_ch, trigger_ch = channels.get('pmt'), channels.get('trigger')
    if pmt_ch not in (1, 2) or trigger_ch not in (1, 2) or pmt_ch == trigger_ch:
        problems.append('SCI.channels.pmt and SCI.channels.trigger must be 1 and 2 in either order')

    range_name = settings['range']
    if range_name not in SCI_RANGE_V:
        problems.append("SCI.range must be 'low' or 'high'")
    limit = SCI_RANGE_V.get(range_name, SCI_RANGE_V['low'])
    _check_sci_signal('pmt', settings.get('pmt'), limit, problems)
    _check_sci_signal('trigger', settings.get('trigger'), limit, problems)

    buffer, pre = settings['buffer_samples'], settings['pre_trigger_samples']
    if not isinstance(buffer, int) or buffer < 32 or buffer % 4:
        problems.append('SCI.buffer_samples must be a multiple of 4 and at least 32')
    elif not isinstance(pre, int) or not 1 <= pre <= SCI_MAX_PRE_TRIGGER or pre + SCI_MIN_POST_TRIGGER > buffer:
        problems.append(f'SCI.pre_trigger_samples must be 1-{SCI_MAX_PRE_TRIGGER} and leave {SCI_MIN_POST_TRIGGER} samples after the trigger in the buffer')
    if settings['save_waveform'] not in (0, 1):
        problems.append('SCI.save_waveform must be 0 or 1')

    if problems:
        raise ConfigError('invalid SCI settings: ' + '; '.join(problems))
