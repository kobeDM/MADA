#!/usr/bin/env python3

import os
import subprocess
from typing import Dict, Optional

MADAHOME  = os.environ['MADAHOME']
FIND_ADALM_EXECUTABLE = MADAHOME + "/bin/FindAdalm"

def _get_adalm_map(executable_path: str = FIND_ADALM_EXECUTABLE) -> Dict[str, str]:
    result = subprocess.run(
        [executable_path],
        capture_output=True,
        text=True,
        check=True
    )

    adalm_map = {}
    current_uri = None

    for line in result.stdout.splitlines():
        line = line.strip()

        if line.startswith("URI"):
            current_uri = line.split(":", 1)[1].strip()

        elif line.startswith("Serial Number"):
            serial = line.split(":", 1)[1].strip()
            if current_uri:
                adalm_map[serial] = current_uri
                current_uri = None

    return adalm_map


def get_uri_by_serial(serial_number: str, executable_path: str = FIND_ADALM_EXECUTABLE) -> Optional[str]:
    adalm_map = _get_adalm_map(executable_path)
    return adalm_map.get(serial_number)


def list_devices(executable_path: str = FIND_ADALM_EXECUTABLE) -> Dict[str, str]:
    return _get_adalm_map(executable_path)


if __name__ == "__main__":
    devices = list_devices()

    if not devices:
        print("No devices found.")
    else:
        print("Detected devices:")
        for serial, uri in devices.items():
            print(f"{serial} -> {uri}")