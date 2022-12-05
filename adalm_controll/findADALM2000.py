#!/usr/bin/python3

import os, sys
import subprocess
import numpy
import glob
import time
import argparse

from subprocess import PIPE

#def print_cmd(cmd):
#    for c in cmd:
#        print(c, end=' ')
#    print()

ADALMPATH="/home/msgc/adalm/adalm_out/bin/"
ADOUT="ad_out"

#venderID="0456"
productID="0456:b672"

#print("argc="+str(sys.argc))
#parser = argparse.ArgumentParser()
#parser.add_argument("arg1",help="S/N to find",action="store_true")
#args = parser.parse_args( )
#print("S/N to find:",args.arg1)

#print(sys.argv)
#print(len(sys.argv))
targetSN=""
if ( len(sys.argv) == 1 ):
    print("List ADALM devices URIs.")
    find=0
else:
    targetSN=sys.argv[1]
#    print("Find the ADALM device URI with S/N:"+targetSN)
    find=1
found=0    
#cmd="lsusb | grep "+productID
cmd="iio_attr -a -C fw_version | grep "+productID
#starter with iio_attr -a -C fw_version
proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=PIPE,text=True)
#print(proc)
#proc=subprocess.run(cmd,shell=True,stdout=PIPE,text=True)
#proc=subprocess.run(cmd,shell=True,stdout=PIPE)
#devices=proc.stdout.split('\n')
#devices=proc.stderr.split(':')
#devices=proc.stderr.split(':')
devices=proc.stderr.split('0456')
#print(devices)
#print(len(devices))
numdev=len(devices)-1
#print(str(numdev)+ " ADALM2000 found.")
usbs=[]
SN=[]
for i in range(numdev):
#    i+=1
#    print(i)
    #print(devices[i+1].split())
    SN.append(devices[i+1].split()[6].split('=')[1])
    usbs.append(devices[i+1].split()[7].split(':')[1].replace(']',''))
    
#    print("usb:"+(str(int((devices[i].split())[1])))+"."+(str(int((devices[i].split())[3].replace(':',''))))+".5")
#    usbs.append("usb:"+(str(int((devices[i].split())[1])))+"."+(str(int((devices[i].split())[3].replace(':',''))))+".5")

#            +"."+(str(int((devices[i].split())[8].replace(':','')))))
#print(devices.split('\n'))
#print(usbs)
#print(SN)

for i in range(len(usbs)):
    cmd=ADALMPATH+ADOUT+" -s -u "+usbs[i] + "| grep serial"
#    cmd=ADALMPATH+ADOUT+" -s -u "+usbs[i] + "| grep serial"
#    print(cmd)
    proc=subprocess.run(cmd,shell=True,stdout=PIPE,text=True)
#    SN= proc.stdout.split('\n')                              
#    SN.append(proc.stdout.split('\n')                              )
#    SN.append((proc.stdout).replace("\n","").split(":")[1])
    if(find==0):
#        print("device "+str(i)+"\t"+usbs[i]+"\t S/N:"+SN[i])
        print("device "+str(i)+"\t"+usbs[i]+"\t S/N:"+SN[i])
    elif (find==1):
        if(SN[i]==targetSN):
#            print("device "+str(i)+"\t"+usbs[i]+"\t S/N:"+SN[i])
#            print("URI for S/N"+SN[i]+": "+usbs[i])
#            print("URI for S/N"+SN[i]+": "+usbs[i])
            print("usb:"+usbs[i])
            found+=1

if(find and not found):
    print("No device with S/N "+targetSN+" found.")
    
