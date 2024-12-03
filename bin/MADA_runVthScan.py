#!/usr/bin/env python3
import subprocess, os,sys
import argparse
import glob
from subprocess import PIPE

print('### MADA_runVthScan.py start ###')

def parser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("IP", type=str, nargs='?', const=None, help='[IP]')
    argparser.add_argument("VthLow", type=int, nargs='?', const=None, help='[V thresholod lower bound]')
    argparser.add_argument("VthHigh", type=int, nargs='?', const=None, help='[V thresholod upper bound]')
    argparser.add_argument("VthStep", type=int, nargs='?', const=None, help='[V thresholod step]')
    argparser.add_argument("-b", "--batch", help="batch mode", dest='batch', action="store_true")
    argparser.add_argument("-d", "--dac", help="dac file path")
    args = argparser.parse_args()
    
    return args

def print_and_exe(cmd):
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


MADAHOME     = os.environ["MADAHOME"]
IWAKIANAHOME = os.environ['IWAKIANAHOME']
MADABIN      = MADAHOME + '/bin/'
IWAKIANABIN  = IWAKIANAHOME + '/bin/'
CONFIGPATH   = MADAHOME + "/config/"

FETCHCONFIG   = MADABIN + "MADA_fetch_config.py"
EXE_SETDAC = MADABIN + "SetDAC"
EXE_DAQ    = IWAKIANABIN + "ScanVth"
EXE_ANA    = MADABIN + "MADA_runVthAna.py"

# Default values
VthLow     = "0"
VthHigh    = "16384"
VthStep    = "32"
batch_mode = 0
DACfile = "/home/msgc/namai/VthScan/v3.1/dac/192.168.100.64_4.dac"
# DACfile = "/home/msgc/namai/VthScan/v3.1/dac/192.168.100.96_1.dac"
# DACfile = "/home/msgc/namai/VthScan/v3.1/DAC_run0022/base_correct.dac"

def main():
    args = parser()
    if args.IP:
        IP=args.IP
    else:
        print("runDACScan [IP] [Vth lower] [Vth upper] [Vth step]")
        sys.exit(1)

    if args.VthLow:
        VthLow = args.VthLow
    else:
        print('Used default VthLow:', VthLow)

    if args.VthHigh:
        VthHigh=args.VthHigh
    else:
        print('Used default VthHigh:', VthHigh)

    if args.VthStep:
        VthStep=args.VthStep
    else:
        print('Used default VthStep:', VthStep)

    if args.batch:
        print("Batch mode")
        batch_mode = 1

    if args.dac:
        DACfile = args.dac
    else:
        print('Used default DACfile:', DACfile)

    cmd = FETCHCONFIG
    ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)
    print(ret.stdout)        

    # write DAC values
    cmd = EXE_SETDAC + " " + IP + " " + DACfile
    print_and_exe(cmd)

    print("IP      :", IP     )
    print("Vth Low :", VthLow )
    print("Vth High:", VthHigh)
    print("Vth Step:", VthStep)
        
    newrun = find_newrun()
    cmd = "mkdir " + newrun
    print_and_exe(cmd)

    os.chdir(newrun)
    cmd = EXE_DAQ + " " + IP + " " + str(VthLow) + " "+str(VthHigh) + " "+str(VthStep)
    print_and_exe(cmd)
    os.chdir("../")

    cmd = "cp " + newrun + "/scan_config.out ."
    print_and_exe(cmd)

    if batch_mode:
        cmd = EXE_ANA + " -b " + newrun
    else:
        cmd = EXE_ANA + " " + newrun
    print_and_exe(cmd)

    cmd = "mv Vthcheck.png Vth.root Vth_val.root " + newrun
    print_and_exe(cmd)

    cmd = "cp " + DACfile + " " + newrun
    print_and_exe(cmd)

    print('### MADA_runVthScan.py end ###')

if __name__ == '__main__':
    main()
