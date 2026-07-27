#!/usr/bin/env python3

import os
import json

from find_adalm2000 import get_uri_by_serial

MADAHOME   = os.environ['MADAHOME']
CONFIGPATH = MADAHOME + '/config'

CONFIG      = 'MADA_config.json'
CONFIG_SKEL = 'MADA_config_SKEL.json'

def run_fetch_config():
    if os.path.isfile(CONFIG):
        print(CONFIG, 'exists.')
    else:
        # Make config file from skelton file
        config_skel = CONFIGPATH + '/' + CONFIG_SKEL
        print('MADA config slkelton file: ', config_skel)
        with open(config_skel, 'r') as file:
            skel_load = json.load(file)

        #set ADALM URIs by checking S/Ns
        for x in skel_load['ADALM']:
            SN = skel_load['ADALM'][x]['S/N']
            URI = get_uri_by_serial(SN)
            skel_load['ADALM'][x]['URI'] = URI
            print('\tS/N:', SN, '-->', skel_load['ADALM'][x]['URI'])

            with open(CONFIG, mode='wt', encoding='utf-8') as file:
                json.dump(skel_load, file, ensure_ascii=False, indent=4)

def main():
    print('### mada_fetch_config.py start ###')
    run_fetch_config()
    print('### mada_fetch_config.py end ###')

if __name__ == '__main__':
    main()