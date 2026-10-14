#!/usr/bin/env python3

from mada_process import stop_processes

TARGET_PROGRAMS = ['AdalmControl']


def run_kill_adalms():
    return stop_processes(TARGET_PROGRAMS, 'ADALM processes')


def main():
    run_kill_adalms()

if __name__ == '__main__':
    main()
