#!/usr/bin/env python3

import subprocess

print('### MADA_killads.py start ###')

modules  = ['MADA_DAQenable', 'ad_out']

killpids = []
for i in range(len(modules)):
    print("kill", modules[i])
    ps = "ps -aux | grep -v \' grep \' | grep " + modules[i]
    process = (subprocess.Popen(ps, stdout=subprocess.PIPE, shell=True).communicate()[0]).decode('utf-8')
    pl = process.split("\n")
    for j in range(len(pl) - 1):
        pll = pl[j].split()
        killpids.append(pll[1])

for i in range(len(killpids) - 1):
    kill = "kill -KILL " + killpids[i]
    subprocess.run(kill,shell=True)

print('### MADA_killads.py end ###')
