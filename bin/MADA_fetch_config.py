#!/usr/bin/env python3

import os
import subprocess
import json
from subprocess import PIPE


MADAHOME   = os.environ['MADAHOME']
BINPATH    = MADAHOME + '/bin'
CONFIGPATH = MADAHOME + '/config'

findADALM   = 'findADALM2000.py'
CONFIG      = 'MADA_config.json'
CONFIG_SKEL = 'MADA_config_SKEL.json'

def main():
    print('### MADA_fetch_config.py start ###')
    
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
            cmd = BINPATH + '/' + findADALM + ' ' + SN
            ret = subprocess.run(cmd, shell=True, stdout=PIPE, stderr=None,  check=False, capture_output=False)
            
            URI = ret.stdout.decode('utf8').replace('\n','')
            skel_load['ADALM'][x]['URI'] = URI
            print('\tS/N:', SN, '-->', skel_load['ADALM'][x]['URI'])    
        
            with open(CONFIG, mode='wt', encoding='utf-8') as file:
                json.dump(skel_load, file, ensure_ascii=False, indent=4)

    print('### MADA_fetch_config.py end ###')

if __name__ == '__main__':
    main()