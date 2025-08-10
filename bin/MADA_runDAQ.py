#!/usr/bin/python3



def main():

    print("**MADA start from MAQS servers**")
    print("**Micacle Argon DAQ (http://github.com/kobeDM/MADA)**")
    print("**2025 Aug by S. Higashino**")

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", help="config file name", default=CONFIG)
    parser.add_argument("-s", help="silent mode (control only)", action='store_true')
    parser.add_argument("-n", help="file size in MB", default=FILE_SIZE)

    args = parser.parse_args()
    current_period = make_new_period()
    
    try:
        start_daq(args, current_period)
    except KeyboardInterrupt:
        print()
        print("===========================")
        print("aborted DAQ")
        print("===========================")

        # proc_daq_disable = subprocess.Popen(DISABLE, shell=True)
        proc_daq_killer = subprocess.Popen(f"{DAQKILLER} -p {current_period} -c {args.c}", shell=True)

        # proc_daq_disable.communicate()
        proc_daq_killer.communicate()
    
if __name__ == "__main__":
    main( )
