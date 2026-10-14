#!/usr/bin/env python3

from mada_process import stop_processes

TARGET_PROGRAMS = ['ad_out', 'MadaIwaki', 'mada_daq_killer']


def run_kill_modules():
    return stop_processes(TARGET_PROGRAMS, 'MADA-related processes')


def main():
    run_kill_modules()

if __name__ == '__main__':
    main()
