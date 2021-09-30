#!/usr/bin/python3

import os,sys
import subprocess


print("MADA_logger.py")

ITtaker=os.environ['HOME']+'/bin/IT6332_mon.py'

#IT6332 start
print(" Starting IT6332A loggin.")
com='nohup '+ITtaker+' > /dev/null &' 
print("  "+com)
subprocess.run(com,shell=True)
