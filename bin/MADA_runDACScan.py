#!/usr/bin/python3
import subprocess
import os
import sys
import argparse
import glob
from subprocess import PIPE

MADAPATH = "/home/msgc/miraclue/MADA/bin"
EXE = "MADA_DACScan"
# ANAPATH="/home/msgc/miraclue/ana/bin"
ANA = "MADA_DACAna"


def parser():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("IP", type=str, nargs='?', const=None, help='[IP]')
    argparser.add_argument("Vth", type=str, nargs='?', const=None, help='[V thresholod]')
    argparser.add_argument("--batch", "-b", action='store_true')
    opts = argparser.parse_args()
    return (opts)


def print_and_exe(cmd):
    print("execute:"+cmd)
    subprocess.run(cmd, shell=True)


def find_newrun():
    dir_header = 'DAC_run'
    files = glob.glob(dir_header+'*')
    if len(files) == 0:
        return dir_header+'0'.zfill(4)
    else:
        files.sort(reverse=True)
        num_pos = files[0].find("run")
        return dir_header+str(int(files[0][num_pos+3:num_pos+3+4])+1).zfill(4)


args = parser()
if (args.IP):
    IP = args.IP
else:
    print("runDACScan.py IP [Vth]")
    sys.exit(1)

if (args.Vth):
    Vth = args.Vth
else:
    Vth = "8800"

newrun = find_newrun()
CMD = "mkdir "+newrun
print_and_exe(CMD)
os.chdir(newrun)
CMD = "mkdir png"
print_and_exe(CMD)

EXECOM = MADAPATH+"/"+EXE+" "+IP+" "+Vth
print_and_exe(EXECOM)
os.chdir("../")

CMD = MADAPATH+"/"+ANA+" "+newrun+" "+Vth
CMD = f'{MADAPATH}/{ANA} {newrun} {Vth} {int(args.batch)}'
print_and_exe(CMD)


COM = "mv DAC.root "+newrun
print_and_exe(COM)


COM = "mv base_correct.dac "+newrun
print_and_exe(COM)

# write DAC_image
cmd = """
echo 'auto c = new TCanvas; DAC_image->Draw("colz"); c->SaveAs("{0}/DAC_image.png");' | root -b {0}/DAC.root 
""".strip().format(newrun)
print_and_exe(cmd)


# concat png
target_file_format = '{}/Ch_{}.png'
for i in range(8):
    target_indexes = [f'{16*i+j:03}' for j in range(16)]
    target_files = [target_file_format.format(newrun, idx)
                    for idx in target_indexes]
    target_files_str = ' '.join(target_files)
    cmd = f'convert +append {target_files_str} {newrun}/col{i}.jpg'
    print_and_exe(cmd)

cols = ' '.join([f'{newrun}/col{i}.jpg' for i in range(i)])
cmd = f'convert -append {cols} {newrun}/DAC.jpg'
print_and_exe(cmd)

# print summary
cmd = f'imgcat {newrun}/DAC_image.png'
print_and_exe(cmd)
