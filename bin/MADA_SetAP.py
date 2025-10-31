#!/usr/bin/env python3

import os
import sys
import subprocess

IWAKIANAHOME = os.environ['IWAKIANAHOME']
IWAKIANABIN = IWAKIANAHOME + '/bin'

SETAP = IWAKIANABIN + "/SetAP"

def main():
    print("*** MADA_SetAP.py start ***")
    if len(sys.argv) < 3:
        print("usage: python3 MADA_SetAP.py [ip] [I/O]")
    ip = sys.argv[1]
    io = sys.argv[2]
    cmd = [SETAP, ip, io]
    print(cmd)
    stdout = subprocess.run(cmd, capture_output=True, text=True).stdout
    print(stdout)
    print("*** MADA_SetAP.py end ***")

if __name__ == "__main__":
    main()