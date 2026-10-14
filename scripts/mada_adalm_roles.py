#!/usr/bin/env python3

"""The ADALM roles of a DAQ run (DAQ enable, counter reset, software veto)
and the DIO lines each role owns. Roles may share one ADALM when their DIO
masks are disjoint."""

from mada_config import ConfigError

ROLE_DAQ_ENABLE = 0
ROLE_COUNTER_RESET = 1
ROLE_VETO = 2

ROLE_NAMES = {
    ROLE_DAQ_ENABLE: 'DAQ enable',
    ROLE_COUNTER_RESET: 'counter reset',
    ROLE_VETO: 'software veto',
}

ALL_LINES = 0xFFFF  # mask of a role that does not set DIO_mask


def _entry(config, index):
    return config.get('ADALM', {}).get('MADALM_' + str(index))


def adalm_role(config, index):
    """(serial, DIO mask) of a role. ConfigError when the role has no S/N."""
    entry = _entry(config, index)
    if not entry or not entry.get('S/N'):
        raise ConfigError(f'ADALM role {ROLE_NAMES.get(index, index)} (MADALM_{index}) has no S/N')

    try:
        mask = int(str(entry.get('DIO_mask', ALL_LINES)), 0)
    except ValueError:
        raise ConfigError(f"MADALM_{index}: DIO_mask {entry['DIO_mask']!r} is not a number")

    if not 0 < mask <= ALL_LINES:
        raise ConfigError(f'MADALM_{index}: DIO_mask {hex(mask)} is out of range')
    return entry['S/N'], mask


def veto_role(config):
    """(serial, mask) of the software veto, or None when it is not configured or inactive."""
    entry = _entry(config, ROLE_VETO)
    if entry is None or entry.get('active', 1) != 1:
        return None
    return adalm_role(config, ROLE_VETO)


def daq_roles(config):
    """{role index: (serial, mask)} for every role in use, checked for DIO conflicts."""
    roles = {
        ROLE_DAQ_ENABLE: adalm_role(config, ROLE_DAQ_ENABLE),
        ROLE_COUNTER_RESET: adalm_role(config, ROLE_COUNTER_RESET),
    }
    veto = veto_role(config)
    if veto:
        roles[ROLE_VETO] = veto

    check_masks(roles)
    return roles


def check_masks(roles):
    """Roles that share one ADALM need disjoint, explicit DIO masks."""
    items = list(roles.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (ra, (sa, ma)), (rb, (sb, mb)) = items[i], items[j]
            if sa != sb:
                continue
            if ma == ALL_LINES or mb == ALL_LINES or (ma & mb):
                raise ConfigError(
                    f'{ROLE_NAMES.get(ra, ra)} and {ROLE_NAMES.get(rb, rb)} share ADALM {sa} '
                    f'but DIO_mask is missing or overlaps ({hex(ma)}, {hex(mb)}); set disjoint DIO_mask in the config')
