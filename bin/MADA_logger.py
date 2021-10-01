#!/usr/bin/python3

import os,sys
import subprocess


print("MADA_logger.py")

ITtaker=os.environ['HOME']+'/bin/IT6332_mon.py'

#IT6332 start
print(" Starting IT6332A logging.")
com='nohup '+ITtaker+' > /dev/null' 
print("  "+com)
print("monitoring IT6332A")
#subprocess.run(com,shell=True)
subprocess.Popen(com,stdout=subprocess.PIPE,shell=True)
