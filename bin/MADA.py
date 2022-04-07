#!/usr/bin/python3

import os, sys
import subprocess
import numpy
import glob
import time,datetime
import argparse
import json
import glob

from subprocess import PIPE
from time import sleep
#from datetime import datetime
#from subprocess import STDOUT

HOME=os.environ["HOME"]

#PATH
MADAPATH=HOME+"/miraclue/MADA/bin/"
ITPATH=HOME+"/ITECH/"
RATEPATH=HOME+"/rate/"
MADACONFIGPATH=HOME+"/miraclue/MADA/config/"

#binary
#MADA="MADA"
#MADACON="MADA_con"
MADAIWAKI="MADA_iwaki"

#scripts
FETCHCON=MADAPATH+"MADA_fetch_config.py"
findADALM=MADAPATH+"findADALM2000.py"
SETDAC=MADAPATH+"MADA_SetAllDACs.py"
ENABLE=MADAPATH+"MADA_DAQenable.py"
DISABLE=MADAPATH+"MADA_DAQenable.py -d"
COUNTERRESET=MADAPATH+"MADA_counterreset.py"
DAQKILLER=MADAPATH+"MADA_DAQkiller.py"
KILLER=MADAPATH+"MADA_killmodules.py"
ADKILLER=MADAPATH+"MADA_killads.py"
POWERRESET=ITPATH+"IT6332_reset.py"

#configs
CONFIG="MADA_config.json"
CONFIG_SKEL="MADA_config_SKEL.json"

sql_dbname="rate"

print("**MADA.py**")
print("**Micacle Argon DAQ (http://github.com/kobeDM/MADA)**")
print("**2021 Sep by K. Miuchi**")

num=1000 #data size in Mbyte
num_max=1000 # max size
run_control=0 #option for run control only

#read option parameters
parser = argparse.ArgumentParser()
parser.add_argument("-c",help="config file name",default=CONFIG)
parser.add_argument("-s",help="silent mode (control only)",action='store_true')
parser.add_argument("-n",help="file size in MB",default=num)
args = parser.parse_args( )
CONFIG=args.c
num=args.n
run_control=args.s

if int(num) > num_max:
    num=num_max

print("data size per file: "+str(num)+" Mbyte")
#fetch config file
#print(FETCHCON)
proc=subprocess.run(FETCHCON,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
#fetch config file ends

#DAC set
if(run_control==0):
#    print(SETDAC)
    proc=subprocess.run(SETDAC,shell=True,stdout=PIPE,stderr=None,check=False,capture_output=False)
#DAC set

        
#load config file
config_open= open(CONFIG,'r')
config_load = json.load(config_open)
activeIP=[]
boardID=[]
for x in config_load['gigaIwaki']:
    if config_load['gigaIwaki'][x]['active']==1:
        activeIP.append(config_load['gigaIwaki'][x]['IP'])
        boardID.append(x)
        print(config_load['gigaIwaki'][x]['IP'])
#load config file ends.
            
print("Number of Iwaki boards: ",len(activeIP))
#print(activeIP.len)



#make new period
p=0
while(os.path.isdir("per"+str(p).zfill(4))):
#      print("per",p," exixts.")
      p+=1

      
newper="per"+str(p).zfill(4)
cmd="mkdir "+newper
proc=subprocess.run(cmd,shell=True)
cmd="cp "+CONFIG+" "+newper
proc=subprocess.run(cmd,shell=True)
print("New directory ",newper,"is made.")



#cmd="cd "+newper
#proc=subprocess.run(cmd,shell=True)
fileperdir=1000
fileID=0
#DAQ run
#while fileID < fileperdir:
# 
#    print(filename_head)
#    cmd='xterm -e '+MADAPATH+MADAIWAKI +" -i "+IP+" -n "+str(num)+ " -f " + filename_head+" &"
#   proc=subprocess.run(cmd,shell=True)
#print(cmd)

#filename_head=newper+"/GBIP_thisIP"
#filename_head=newper+"/GBKB_thisIP"
#if(run_control):
#    cmd=MADAPATH+MADA+" -s "+" -n "+str(num)+" -f "+str(filename_head)

    #    cmd=MADAPATH+MADACON
#cmd=MADAPATH+MADACON
#proc=subprocess.run(cmd,shell=True)
#+" -n "+str(num)
#else:
#filename_head=newper+"/GBIP_thisIP_"+str(fileID).zfill(4)
#    cmd=MADAPATH+MADA+" -n "+str(num)+" -f "+str(filename_head)
#    print(cmd)
    #proc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None,Text=True)
    #proc=
#    subprocess.run(cmd,shell=True)



fileID=0

# database setting for rate
import pymysql.cursors
conn = pymysql.connect(host='10.37.0.214',port=3306,user='rubis',passwd='password',autocommit='true')
cursor = conn.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS " + sql_dbname)
cursor.execute("USE " + sql_dbname)
cursor.execute("CREATE TABLE IF NOT EXISTS  MADA_rate(time TIMESTAMP not null default CURRENT_TIMESTAMP,start FLOAT,end FLOAT,ch0_size FLOAT,ch1_size FLOAT,ch2_size FLOAT,ch3_size FLOAT,ch0_rate FLOAT,ch1_rate FLOAT,ch2_rate FLOAT,ch3_rate FLOAT)")

subprocess.run(KILLER,shell=True)

cmd="xterm -geometry 50x5+800+600 -title 'MADA killer' -background black -foreground green -e "+DAQKILLER+" -p "+str(newper)
prockiller=subprocess.Popen(cmd,shell=True)



#DAQ run
while fileID < fileperdir:
 #   subprocess.run(POWERRESET,shell=True)
    print(fileID,"/",fileperdir)
    #print(DISABLE)
    subprocess.run(ADKILLER,shell=True)
    subprocess.run(DISABLE,shell=True)
    pids=[]
    for i in range(len(activeIP)):
        IP=activeIP[i]
#        filename_head=newper+"/GBKB_"+IP.split(".")[3].zfill(3)+"_"+str(fileID).zfill(4)
        filename_head=newper+"/"+boardID[i]+"_"+str(fileID).zfill(4)
        filename_info=filename_head+".info"
        filename_mada=filename_head+".mada"
        print("board "+IP+" info was written in "+filename_info)
#        dict={}
#        for x in config_load['gigaIwaki']:
#            if (config_load['gigaIwaki'][x]['IP']==IP):
#                dict.update(config_load['gigaIwaki'][x])
#                dd={"gigaIwaki":dict}
#                with open(filename_info, mode='wt', encoding='utf-8') as file:
#                    json.dump(dd, file, ensure_ascii=False, indent=2)
                    #wirte info file done

#        exit(0)                    
        print(IP)
        cmd="xterm -geometry 50x10+50+"+str(i*200)+" -e "+MADAIWAKI+" -n "+str(num)+" -f "+str(filename_mada)+" -i "+IP 
        print(cmd)
        #roc=subprocess.run(cmd,shell=True,stdout=PIPE,stderr=None)
        proc=subprocess.Popen(cmd,shell=True,stdout=PIPE,stderr=None)
        pids.append(proc.pid)
        
    cmd="xterm -geometry 50x10+400+0 -e "+ENABLE
    #cmd=ENABLE+" &"
    starttime=time.time()#.now().timestamp()
    proc=subprocess.Popen(cmd,shell=True)
    enablepid=proc.pid

    for i in range(len(activeIP)):
        IP=activeIP[i]
        filename_head=newper+"/"+boardID[i]+"_"+str(fileID).zfill(4)
        filename_info=filename_head+".info"
        dict={}
        for x in config_load['gigaIwaki']:
            if (config_load['gigaIwaki'][x]['IP']==IP):
                dict.update(config_load['gigaIwaki'][x])
                dd={"gigaIwaki":dict}
                dmes={}
                dmes['start']=starttime
                ddmes={"runinfo":dmes}
                dd.update(ddmes)
                #                dinfo={"gigaIwaki":dd,"runinfo":ddmes}
                
                with open(filename_info, mode='wt', encoding='utf-8') as file:
                    json.dump(dd, file, ensure_ascii=False, indent=2) 
            
    subprocess.run(COUNTERRESET,shell=True)
#    enablepid=proc.pid
    print("GIGAiwaki pids: ",pids)    
    print("enable pid: ",enablepid)    
    print("working directory: ",newper)
    print("started at ",starttime)

    running=1
#    ps="ps -aux "
    while running:
#        sleep(1)
        runs=0
        for i in range(len(pids)):
            cmd='ps -aux | awk \'$2=='+str(pids[i])+'\' | wc -l'
#            subprocess.run(cmd,
#                          shell=True)
                           #.communicate()[0].decode('utf-8')
            pnum = (subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        shell=True).communicate()[0]).decode('utf-8')
#            print("number of proscess: ",pnum)
            if int(pnum) == 1:
                runs+=1
 
#        print("running IDs",runs)
        if runs < len(pids):
            running=0
            print("file terminate")
            #kill="kill -KILL "+str(enablepid)
            #subprocess.run(kill,shell=True)
            subprocess.run(ADKILLER,shell=True)
            subprocess.run(DISABLE,shell=True)
            endtime=time.time()#.now().timestamp()


            ps="ps -aux | grep -v \' grep \' | grep xterm | grep iwaki "
            process = (subprocess.Popen(ps, stdout=subprocess.PIPE,
                                shell=True).communicate()[0]).decode('utf-8')
            pl=process.split("\n")
            killpids=[]
            for j in range(len(pl)-1):
                pll=pl[j].split()
                #        print(pll)
                killpids.append(pll[1])
                #print(killpids)
                for i in range(len(killpids)):
                    kill="kill -KILL "+killpids[i]
                    subprocess.run(kill,shell=True)
    
            break
            #            proc.poll()
            
    
            #        print(".",end="")
    print("file ",fileID," finished at ",str(endtime))
    realtime=endtime-starttime
    print("real time=",str(realtime))
    size=[]
    for i in range(len(activeIP)):
        filename_head=newper+"/"+boardID[i]+"_"+str(fileID).zfill(4)
        filename_info=filename_head+".info"
        filename_mada=filename_head+".mada"
        cmd='ls -l '+filename_mada
        #proc=subprocess.run(cmd,shell=True)
#        proc = (subprocess.Popen(cmd, stdout=subprocess.PIPE,
#                         shell=True).communicate()[0]).decode('utf-8')
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         shell=True).communicate()[0].decode('utf-8')
        print(proc)
        sizel=str(proc).split()
#        print
        print("size= ",str(sizel[4]),"byte")
        dmes={}
#        dmes['start']=starttime
        dmes['end']=endtime
        dmes['size']=sizel[4]
        size.append(sizel[4])
        ddmes={"runinfo":dmes}
        info_open= open(filename_info,'r')
        info_load = json.load(info_open)
        dict_giga={}
        dict_info={}
        for x in info_load['gigaIwaki']:
#            dict_giga.update(info_load['gigaIwaki'][x])
            dict_giga.update(info_load['gigaIwaki'])
        for x in info_load['runinfo']:
#            dict_info.update(info_load['runinfo'][x])
            dict_info.update(info_load['runinfo'])
        dict_info.update(dmes)
        dict={"gigaIwaki":dict_giga,"runinfo":dict_info}
        with open(filename_info, mode='w', encoding='utf-8') as file:
            json.dump(dict, file, ensure_ascii=False, indent=2)
            
#        with open(filename_info, encoding='utf-8') as file:
#            data_lines=file.read()
#        data_lines=data_lines.replace("}{",",")
#        with open(filename_info, mode="w",encoding='utf-8') as file:
#            file.write(data_lines)
    y  =    str(datetime.datetime.fromtimestamp(endtime).year)
    m  =    str(datetime.datetime.fromtimestamp(endtime).month)
    d  =    str(datetime.datetime.fromtimestamp(endtime).day)
    hh  =    str(datetime.datetime.fromtimestamp(endtime).hour)
    mm  =    str(datetime.datetime.fromtimestamp(endtime).minute)
    ss  =    str(datetime.datetime.fromtimestamp(endtime).second)
    ofile=RATEPATH+y+m.zfill(2)+d.zfill(2)#+"_"+str(i)
    t=y+"/"+m.zfill(2)+"/"+d.zfill(2)+"/"+hh.zfill(2)+":"+mm.zfill(2)+":"+ss.zfill(2)

        
    f = open(ofile, 'a')
    #f.write(t+"\t")
    #print
    # s=t+"\t"+str(starttime)+"\t"+str(endtime)+"\t"+str(sizel[4])+"\t"+str(float(sizel[4])/(endtime-starttime))+"\n"
    #print(s)
    #f.write(s)
    rate=[]
    for ii in range(4):
        rate.append(float(size[ii])/realtime);
#    rate[1]=float(size[1])/realtime;
#    rate[2]=float(size[2])/realtime;
#    rate[3]=float(size[3])/realtime;
    f.write(t+"\t"+str(starttime)+"\t"+str(endtime)+"\t"+str(size[0])+"\t"+str(size[1])+"\t"+str(size[2])+"\t"+str(size[3])+"\t"+str(float(size[0])/realtime)+"\t"+str(float(size[1])/realtime)+"\t"+str(float(size[2])/realtime)+"\t"+str(float(size[3])/realtime)+"\n")
    f.close()

    
    #    cursor.execute("CREATE TABLE IF NOT EXISTS  MADA_rate(time TIMESTAMP not null default CURRENT_TIMESTAMP,start,end,ch0_size FLOAT,ch1_size FLOAT,ch2_size FLOAT,ch3_size FLOAT,ch0_rate FLOAT,ch1_rate FLOAT,ch2_rate FLOAT,ch3_rate FLOAT)")

    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("insert into MADA_rate(start,end,ch0_size,ch1_size,ch2_size,ch3_size,ch0_rate,ch1_rate,ch2_rate,ch3_rate) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",(str(starttime),str(endtime),str(size[0]),str(size[1]),str(size[2]),str(size[3]),str(rate[0]),str(rate[1]),str(rate[2]),str(rate[3])))


    #(str(float((polarities[0]+voltages[0]))),currents[0],str(float((polarities[1]+voltages[1]))),currents[1],str(float((polarities[2]+voltages[2]))),currents[2],str(float((polarities[3]+voltages[3]))),currents[3]))



    fileID+=1
    
