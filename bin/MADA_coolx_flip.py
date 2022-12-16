#!/usr/bin/python3

import libm2k as l
from adalm_controll import m2k_open

# adalm2に4.5Vのパルスを一発入れるスクリプト
# amp = 4.5V, width = 1.25 ms

# adalm2
SERIAL_NUMBER = "104473961406000b03003800c90049e980"
CHANNEL = 0

ctx: l.M2k = m2k_open(SERIAL_NUMBER)
aout: l.M2kAnalogOut = ctx.getAnalogOut()
aout.setSampleRate(CHANNEL, 7.5e7)
aout.enableChannel(CHANNEL, True)
aout.push(CHANNEL, [3 for _ in range(100)])
aout.push(CHANNEL, [0 for _ in range(100)])  # これが大事
