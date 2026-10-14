#!/usr/bin/env python3

"""Read the regulator (AP) state of a board."""

import os
import subprocess

MADAHOME = os.environ['MADAHOME']
READCTRLMEM = MADAHOME + '/bin/ReadCtrlMem'


def get_ap_state(ip):
    """True/False for regulator (AP) on/off read from register 0xf1, or None if unreadable."""
    try:
        out = subprocess.run([READCTRLMEM, ip, '0xf0', '0x10'], capture_output=True, text=True, timeout=10).stdout
    except (subprocess.TimeoutExpired, OSError):
        return None

    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == 'f0':
            return bool(int(parts[2], 16) & 1)
    return None
