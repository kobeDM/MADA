#!/usr/bin/python3

import subprocess
import time
import signal
from typing import Optional
import libm2k
import numpy as np

# aout channel 0 -> self trigger veto
# aout channel 1 -> muon trigger veto
MADA = "/home/msgc/miraclue/MADA/bin/MADA.py"
FIND_ADALM = "/home/msgc/miraclue/MADA/bin/findADALM2000.py"
AD_OUT = "/home/msgc/adalm/adalm_out/bin/ad_out"
MADALM2_SERIAL_NUMBER = "104473961406000b03003800c90049e980"
NIM_HIGH = [-1] * 1024
NIM_LOW = [0] * 1024
RUN_DIRATION = 3600 # 1 hour

def find_adalm2000(serial_number: str) -> Optional[str]:
    """
    usb接続されているadalmの中からserial numberで検索, 存在していたらURIを返す
    """
    proc = subprocess.run([FIND_ADALM, serial_number], stdout=subprocess.PIPE)
    ret = proc.stdout.decode("utf8").replace("\n","")
    if ret.startswith("No device"):
        return None
    else:
        return ret

adalm_url = find_adalm2000(MADALM2_SERIAL_NUMBER)
ctx: libm2k.M2k = libm2k.m2kOpen(adalm_url)
if ctx is None:
    print("Connection Error: No ADALM2000 device available/connected to your PC.")
    exit(1)
aout: libm2k.M2kAnalogOut = ctx.getAnalogOut()
aout.reset()
ctx.calibrateADC()
ctx.calibrateDAC()
aout.setSampleRate(0, 750000)
aout.setSampleRate(1, 750000)
aout.enableChannel(0, True)
aout.enableChannel(1, True)
aout.setCyclic(True)

counter = 0
while True:
    if counter % 2 == 0:
        # BG run
        # self trigger veto (channel0) is low
        aout.push(0, NIM_LOW)
        # muon trigger veto (channel1) is high
        aout.push(1, NIM_HIGH)
        proc = subprocess.Popen([MADA, "-n10"])
    else:
        # muon run
        # self trigger veto (channel 0) is high
        aout.push(0, NIM_HIGH)
        # muon trigger veto (channel 1) is low
        aout.push(1, NIM_LOW)
        proc = subprocess.Popen([MADA, "-n1"])

    time.sleep(30)
    print("👺 sleeped 10 sec")
    # time.sleep(RUN_DIRATION)
    proc.send_signal(signal.SIGINT)
    counter += 1