import subprocess
from subprocess import PIPE
import argparse
import re
import libm2k as l


def findURI(serial_number: str) -> str:
    """
    iio_attrでアナデバのデバイスを一覧して, 
    その結果をいい感じにregexして, 
    adalmのURLを取得する
    """
    iio_attr_cmd = "iio_attr -a -C fw_version"
    proc = subprocess.run(iio_attr_cmd, shell=True,
                          stdout=PIPE, stderr=PIPE, text=True)
    iio_attr_result = proc.stderr.split('\n')[0:]
    target_result = filter(
        lambda res: serial_number in res, iio_attr_result).__next__()
    uri = re.findall("(?<=\[).+?(?=\])", target_result)[0]
    return uri


def m2k_open(serial_number: str) -> l.M2k:
    try:
        ctx = l.m2kOpen(findURI(serial_number))
    except:
        print(f"SN: {serial_number} open error")
        print("check ADALMs existance using 'iio_attr -a -C fw_version' command")
        exit(1)
    return ctx


def init(dig: l.M2kDigital):
    for ch in range(16):
        dig.setOutputMode(ch, 1)
        dig.setDirection(ch, 1)
    dig.setCyclic(False)


def set_digital(dig: l.M2kDigital, level: bool):
    for i in range(8):
        nega_channel = i
        posi_channel = i + 8
        dig.setValueRaw(nega_channel, 0 if level else 1)
        dig.setValueRaw(posi_channel, 1 if level else 0)


def daq_enable_latch(signal: bool):
    """
    daq enableに信号を出す
    adalmのserialはハードコーディング
    signal: True => latch up
    signal: False => latch down
    """
    adalm0_serial_number = "10447384b904001612002500df1edb6193"
    ctx = m2k_open(adalm0_serial_number)
    dig: l.M2kDigital = ctx.getDigital()
    set_digital(dig, not signal)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("signal_level", type=bool,
                        help="false => latch down, true => latch up")
    args = parser.parse_args()
    daq_enable_latch(args.signal_level)


if __name__ == "__main__":
    main()
