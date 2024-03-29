#!/usr/bin/python3

import argparse
import datetime
import json
import os
import subprocess
import time
from subprocess import PIPE

HOME = os.environ["HOME"]

# PATH
MADAPATH = HOME+"/miraclue/MADA/bin/"
RATEPATH = HOME+"/rate/"
MADACONFIGPATH = HOME+"/miraclue/MADA/config/"
ITPATH = HOME+"/SCSM/ITECH/"

# binary
MADAIWAKI = "MADA_iwaki"

# scripts
FETCHCON = MADAPATH+"MADA_fetch_config.py"
ENABLE = MADAPATH+"MADA_DAQenable.py"
DISABLE = MADAPATH+"MADA_DAQenable.py -d"
COUNTERRESET = MADAPATH+"MADA_counterreset.py"
DAQKILLER = MADAPATH+"MADA_DAQkiller.py"
KILLER = MADAPATH+"MADA_killmodules.py"
ADKILLER = MADAPATH+"MADA_killads.py"
DACSET = MADAPATH+"MADA_SetAllDAC.py"
IT6332A_MON=ITPATH+"IT6332_mon.py -o"
IT6332A_OUT=ITPATH+"IT6332_out_chs.py" 

# configs
CONFIG = "MADA_config.json"

sql_dbname = "rate6ch"

FILE_SIZE = 1000  # data size in Mbyte
MAX_FILE_SIZE = 1000  # max size
MAX_BOARDS = 6
ALL_BOARDS = [
    'GBKB-00',
    'GBKB-01',
    'GBKB-03',
    'GBKB-10',
    'GBKB-11',
    'GBKB-13',
]
LV_SETVALUES=[0,0,0]
LV_THREHOLDSS=[0,0,0]
run_control = 0  # option for run control only

print("**MADA.py**")
print("**Micacle Argon DAQ (http://github.com/kobeDM/MADA)**")
print("**2021 Sep by K. Miuchi**")


def make_new_period() -> str:
    """
    カレントディレクトリを走査して新しいperXXXXディレクトリを作成する
    """
    p = 0
    while (os.path.isdir("per"+str(p).zfill(4))):
        p += 1

    newper = "per" + str(p).zfill(4)
    cmd = "mkdir " + newper
    subprocess.run(cmd, shell=True)

    return newper


def start_daq(args, newper):
    mada_config_path = args.c
    file_size = args.n
    run_control = args.s

    if int(file_size) > MAX_FILE_SIZE:
        file_size = MAX_FILE_SIZE

    print("data size per file: "+str(file_size)+" Mbyte")
    # fetch config file
    proc = subprocess.run(FETCHCON, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)

    # load config file
    #config_open = open(mada_config_path, 'r')
    with open(mada_config_path, 'r') as config_open :
        config_load = json.load(config_open)
    activeIP = []
    boardID = []
    for x in config_load['gigaIwaki']:
        if config_load['gigaIwaki'][x]['active'] == 1:
            activeIP.append(config_load['gigaIwaki'][x]['IP'])
            boardID.append(x)
            print(config_load['gigaIwaki'][x]['IP'])

    
    # load config file ends.

    print(f"Number of Iwaki boards: {len(activeIP)}/{MAX_BOARDS}")
    # print(activeIP.len)

    cmd = "cp "+mada_config_path+" "+newper
    proc = subprocess.run(cmd, shell=True)

    fileperdir = 10000
    fileID = 0

    # database setting for rate
    import pymysql.cursors
    conn = pymysql.connect(host='10.37.0.214', port=3306, user='rubis', passwd='password', autocommit='true')
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS " + sql_dbname)
    cursor.execute("USE " + sql_dbname)
    cursor.execute("CREATE TABLE IF NOT EXISTS  MADA_rate(time TIMESTAMP not null default CURRENT_TIMESTAMP,start FLOAT,end FLOAT,ch0_size FLOAT,ch1_size FLOAT,ch2_size FLOAT,ch3_size FLOAT,ch4_size FLOAT,ch5_size FLOAT,ch0_rate FLOAT,ch1_rate FLOAT,ch2_rate FLOAT,ch3_rate FLOAT,ch4_rate FLOAT,ch5_rate FLOAT)")

    subprocess.run(KILLER, shell=True)
    com=IT6332A_OUT+" "+str(config_load['LV']["SET_VALUES"]["ch1"])+" "+ str(config_load['LV']["SET_VALUES"]["ch2"])+" "+str(config_load['LV']["SET_VALUES"]["ch3"])
    proc=subprocess.run(com, shell=True, stdout=subprocess.PIPE)
    # DAQ run
    while fileID < fileperdir:
        print(fileID, "/", fileperdir)
        subprocess.run(ADKILLER, shell=True)
        subprocess.run(DISABLE, shell=True)
        #LV check
        print("LV check")
        with open(mada_config_path, 'r') as config_open :
            config_load = json.load(config_open)
        
        #print(config_load['LV'])
        proc=subprocess.run(IT6332A_MON, shell=True, stdout=subprocess.PIPE)
        LVvalues=proc.stdout.split()
        print(LVvalues)
        if float(LVvalues[2]) > config_load['LV']["TH_VALUES"]["ch1"] or float(LVvalues[4]) > config_load['LV']["TH_VALUES"]["ch2"] or float(LVvalues[6]) > config_load['LV']["TH_VALUES"]["ch3"]:
            #threshold over
            print("threhold over")
            com=IT6332A_OUT+" "+str(config_load['LV']["SET_VALUES"]["ch1"])+" 0 0"
            #print(com)
            proc=subprocess.run(com, shell=True, stdout=subprocess.PIPE)
            com=IT6332A_OUT+" "+str(config_load['LV']["SET_VALUES"]["ch1"])+" "+ str(config_load['LV']["SET_VALUES"]["ch2"])+" "+str(config_load['LV']["SET_VALUES"]["ch3"])
            proc=subprocess.run(com, shell=True, stdout=subprocess.PIPE)
            #print(com)
            #proc=subprocess.run(com, shell=True, stdout=subprocess.PIPE)
            #DAC reset 
            #subprocess.run(DACSET, shell=True)

        #exit(0)
        

        
        pids = []
        for i in range(len(activeIP)):
            IP = activeIP[i]
            filename_head = newper+"/"+boardID[i]+"_"+str(fileID).zfill(4)
            filename_info = filename_head+".info"
            filename_mada = filename_head+".mada"
            print("board "+IP+" info was written in "+filename_info)
            print(IP)
            cmd = "xterm -geometry 50x10+50+"+str(i*200)+" -e "+MADAIWAKI+" -n " + \
                str(file_size)+" -f "+str(filename_mada)+" -i "+IP
            print(cmd)
            proc = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=None)
            pids.append(proc.pid)

        cmd = "xterm -geometry 50x10+400+0 -e "+ENABLE
        starttime = time.time()
        proc = subprocess.Popen(cmd, shell=True)
        enablepid = proc.pid

        for i in range(len(activeIP)):
            IP = activeIP[i]
            filename_head = newper+"/"+boardID[i]+"_"+str(fileID).zfill(4)
            filename_info = filename_head+".info"
            dict = {}
            for x in config_load['gigaIwaki']:
                if (config_load['gigaIwaki'][x]['IP'] == IP):
                    dict.update(config_load['gigaIwaki'][x])
                    dd = {"gigaIwaki": dict}
                    dmes = {}
                    dmes['start'] = starttime
                    ddmes = {"runinfo": dmes}
                    dd.update(ddmes)
                    with open(filename_info, mode='wt', encoding='utf-8') as file:
                        json.dump(dd, file, ensure_ascii=False, indent=2)

        subprocess.run(COUNTERRESET, shell=True)
        print("GIGAiwaki pids: ", pids)
        print("enable pid: ", enablepid)
        print("working directory: ", newper)
        print("started at ", starttime)

        running = 1
        while running:
            runs = 0
            for i in range(len(pids)):
                cmd = 'ps -aux | awk \'$2=='+str(pids[i])+'\' | wc -l'
                pnum = (subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                         shell=True).communicate()[0]).decode('utf-8')
                if int(pnum) == 1:
                    runs += 1

            if runs < len(pids):
                running = 0
                print("file terminate")
                subprocess.Popen(ADKILLER, shell=True)
                subprocess.Popen(DISABLE, shell=True)
                endtime = time.time()

                ps = "ps -aux | grep -v \' grep \' | grep xterm | grep iwaki "
                process = subprocess.Popen(ps, stdout=subprocess.PIPE, shell=True).communicate()[0].decode('utf-8')
                pl = process.split("\n")
                killpids = []
                for j in range(len(pl)-1):
                    pll = pl[j].split()
                    #        print(pll)
                    killpids.append(pll[1])
                    # print(killpids)
                    for i in range(len(killpids)):
                        kill = "kill -KILL "+killpids[i]
                        subprocess.Popen(kill, shell=True)
                break

        print("file ", fileID, " finished at ", str(endtime))
        realtime = endtime-starttime
        print("real time=", str(realtime))
        size = {bid: 0 for bid in ALL_BOARDS}
        for i in range(len(activeIP)):
            filename_head = newper+"/"+boardID[i]+"_"+str(fileID).zfill(4)
            filename_info = filename_head+".info"
            filename_mada = filename_head+".mada"
            cmd = 'ls -l '+filename_mada
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    shell=True).communicate()[0].decode('utf-8')
            print(proc)
            sizel = str(proc).split()
            print("size= ", str(sizel[4]), "byte")
            dmes = {}
            dmes['end'] = endtime
            dmes['size'] = sizel[4]
            # size.append(sizel[4])
            size[boardID[i]] = sizel[4]
            ddmes = {"runinfo": dmes}
            info_open = open(filename_info, 'r')
            info_load = json.load(info_open)
            dict_giga = {}
            dict_info = {}
            for x in info_load['gigaIwaki']:
                dict_giga.update(info_load['gigaIwaki'])
            for x in info_load['runinfo']:
                dict_info.update(info_load['runinfo'])
            dict_info.update(dmes)
            dict = {"gigaIwaki": dict_giga, "runinfo": dict_info}
            with open(filename_info, mode='w', encoding='utf-8') as file:
                json.dump(dict, file, ensure_ascii=False, indent=2)

        y = str(datetime.datetime.fromtimestamp(endtime).year)
        m = str(datetime.datetime.fromtimestamp(endtime).month)
        d = str(datetime.datetime.fromtimestamp(endtime).day)
        hh = str(datetime.datetime.fromtimestamp(endtime).hour)
        mm = str(datetime.datetime.fromtimestamp(endtime).minute)
        ss = str(datetime.datetime.fromtimestamp(endtime).second)
        ofile = RATEPATH+y+m.zfill(2)+d.zfill(2)
        t = y+"/"+m.zfill(2)+"/"+d.zfill(2)+"/"+hh.zfill(2)+":"+mm.zfill(2)+":"+ss.zfill(2)

        # write out event rate into DB and tsb
        # starttime, endtime, mada size, , , mada size / realtime, , ,
        with open(ofile, 'a') as f:
            rate = {bid: 0 for bid in ALL_BOARDS}
            for ii in range(len(activeIP)):
                rate[boardID[ii]] = float(size[boardID[ii]]) / realtime
                # out_list = [t, starttime, endtime] + size + [float(s) / realtime for s in size]
                # out_str = "\t".join(map(str, out_list)) + "\n"
                f.write(f"{size}\t{rate}\n")

        # boardが6枚未満の時にrateとsizeのdictを補完する
        inactive_board = list(set(ALL_BOARDS) - set(boardID))
        for bid in inactive_board:
            size[bid] = 0
            rate[bid] = 0
        try:
            date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "insert into MADA_rate(start,end,ch0_size,ch1_size,ch2_size,ch3_size,ch4_size,ch5_size,ch0_rate,ch1_rate,ch2_rate,ch3_rate,ch4_rate,ch5_rate) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    str(starttime), str(endtime),
                    str(size['GBKB-00']), str(size['GBKB-01']), str(size['GBKB-03']),
                    str(size['GBKB-10']), str(size['GBKB-11']), str(size['GBKB-13']),
                    str(rate['GBKB-00']), str(rate['GBKB-01']), str(rate['GBKB-03']),
                    str(rate['GBKB-10']), str(rate['GBKB-11']), str(rate['GBKB-13']),
                ))
        except:
            import sys
            print("mysql insert error", file=sys.stderr)

        fileID += 1


def main():
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

        # DAQ enableを lowに
        proc_daq_disable = subprocess.Popen(DISABLE, shell=True)
        # DAQKILLER は色々終了処理する (infoファイルの終了時間のtimestampとか)
        proc_daq_killer = subprocess.Popen(f"{DAQKILLER} -p {current_period} -c {args.c}", shell=True)

        proc_daq_disable.communicate()
        proc_daq_killer.communicate()


main()
