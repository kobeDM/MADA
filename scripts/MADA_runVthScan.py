#!/usr/bin/env python3

import os
import subprocess
import argparse
import glob
from subprocess import PIPE

MADAHOME = os.environ["MADAHOME"]

FETCHCONFIG = MADAHOME + "/scripts/MADA_fetch_config.py"
EXE_SETDAC  = MADAHOME + "/bin/SetDAC"
EXE_DAQ     = MADAHOME + "/bin/ScanVth"
EXE_ANA     = MADAHOME + "/scripts/MADA_runVthAna.py"
EXE_CORR    = MADAHOME + "/rootmacro/DACValueCorrection.cxx"

DEFAULT_DACFILE = MADAHOME + "/config/No00_base_v3.1.dac"

def parser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("ip", type=str, nargs='?', const=None, help='[IP]')
    argparser.add_argument("VthLow", type=int, nargs='?', const=None, help='[V thresholod lower bound]', default=0)
    argparser.add_argument("VthHigh", type=int, nargs='?', const=None, help='[V thresholod upper bound]', default=16384)
    argparser.add_argument("VthStep", type=int, nargs='?', const=None, help='[V thresholod step]', default=32)
    argparser.add_argument("-b", "--batch", help="batch mode", action="store_true")
    argparser.add_argument("-d", "--dac", help="dac file path", default=DEFAULT_DACFILE)
    argparser.add_argument("-c", "--correct", help="correct dac value", action="store_true")
    args = argparser.parse_args()
    
    return args

def run_command(cmd):
    print("Execute: " + cmd)
    subprocess.run(cmd, shell=True)

def find_newrun():
    dir_header = 'Vth_run'
    files = glob.glob(dir_header + '*')
    if len(files) == 0:
        newrun = dir_header + '0'.zfill(4)
    else:
        files.sort(reverse=True)
        num_pos = files[0].find("run")
        newrun = dir_header + str(int(files[0][num_pos + 3:num_pos + 3 + 4]) + 1).zfill(4)
    
    return newrun


def main():
    print('### MADA_runVthScan.py start ###')
    
    # Default values
    args = parser()
    ip = args.ip
    VthLow = args.VthLow
    VthHigh = args.VthHigh
    VthStep = args.VthStep
    batch_mode = args.batch
    DACfile = args.dac

    cmd = FETCHCONFIG
    ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
    print(ret.stdout)        

    # write DAC values
    cmd = EXE_SETDAC + " " + ip + " " + DACfile
    run_command(cmd)

    print("IP      :", ip     )
    print("Vth Low :", VthLow )
    print("Vth High:", VthHigh)
    print("Vth Step:", VthStep)
        
    newrun = find_newrun()
    cmd = "mkdir " + newrun
    run_command(cmd)

    os.chdir(newrun)
    cmd = EXE_DAQ + " " + ip + " " + str(VthLow) + " "+str(VthHigh) + " "+str(VthStep)
    run_command(cmd)
    os.chdir("../")

    cmd = "cp " + newrun + "/scan_config.out ."
    run_command(cmd)

    if batch_mode:
        cmd = EXE_ANA + " -b " + newrun
    else:
        cmd = EXE_ANA + " " + newrun
    run_command(cmd)

    cmd = "mv Vthcheck.png Vth.root Vth_val.root " + newrun
    run_command(cmd)

    cmd = "cp " + DACfile + " " + newrun
    run_command(cmd)

    if args.correct:
        print("--- DAC value correction ---")
        rootfile = newrun + "/Vth_val.root"
        dacfile = glob.glob(newrun + "/*.dac")[0]
        print("Corrected DAC file: " + dacfile)
        outputfile = dacfile.replace('.dac', '') + "_correct.dac"
        cmd = "root -l -b -q \'" + EXE_CORR + "(\"" + rootfile + "\", " + "\"" + dacfile + "\", " + "\"" + outputfile + "\")\'"
        run_command(cmd) # Correct branch date is not filled to rootfile currently.

    print('### MADA_runVthScan.py end ###')


if __name__ == '__main__':
    main()
