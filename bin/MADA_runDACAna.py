#!/usr/bin/python3

import subprocess
import argparse


def print_and_exe(cmd):
    print(f"execute: {cmd}")
    subprocess.run(cmd, shell=True)


def run_DACAna(DAC_run_dir: str, Vth: int, is_batch: bool):
    # run analyze
    cmd = f'MADA_DACAna {DAC_run_dir} {Vth} {int(is_batch)}'
    print_and_exe(cmd)

    # write DAC_image
    cmd = """
    echo 'auto c = new TCanvas; DAC_image->Draw("colz"); c->SaveAs("{0}/DAC_image.png");' | root -b {0}/DAC.root 
    """.strip().format(DAC_run_dir)
    print_and_exe(cmd)

    # concat png
    target_file_format = '{}/Ch_{}.png'
    for i in range(8):
        target_indexes = [f'{16*i+j:03}' for j in range(16)]
        target_files = [target_file_format.format(DAC_run_dir, idx)
                        for idx in target_indexes]
        target_files_str = ' '.join(target_files)
        cmd = f'convert +append {target_files_str} {DAC_run_dir}/col{i}.jpg'
        print_and_exe(cmd)

    cols = ' '.join([f'{DAC_run_dir}/col{i}.jpg' for i in range(i)])
    cmd = f'convert -append {cols} {DAC_run_dir}/DAC.jpg'
    print_and_exe(cmd)

    # print summary
    cmd = f'imgcat {DAC_run_dir}/DAC_image.png'
    print_and_exe(cmd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", type=str, nargs='?', const=None, help='[DAC_runXXXX]')
    parser.add_argument("Vth", type=int, nargs='?', const=None, help='[V thresholod]')
    parser.add_argument("--batch", "-b", action='store_true')

    args = parser.parse_args()

    run_DACAna(args.dir, args.Vth, args.batch)


if __name__ == "__main__":
    main()
