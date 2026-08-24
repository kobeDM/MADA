#!/usr/bin/env python3

import psutil

target_modules = [
    'ad_out',
    'MadaIwaki',
    'mada_daq_killer'
]

def run_kill_modules():
    killed_pids = set()

    for proc in psutil.process_iter(['pid', 'cmdline']):
        cmdline = ' '.join(proc.info['cmdline'] or [])

        if any(module in cmdline for module in target_modules):
            print(f"Killing PID {proc.pid}: {cmdline}")
            proc.terminate()
            killed_pids.add(proc.pid)

    if not killed_pids:
        print("No MADA-related processes found to kill.")

    return killed_pids


def main():
    run_kill_modules()

if __name__ == '__main__':
    main()