#!/usr/bin/python3
import os
import time
import datetime
import json
import argparse
import subprocess
from subprocess import PIPE
import MADA_defs as MADADef
import MADA_util as MADAUtil


def make_new_period() -> str:
    per_number = 0
    while os.path.isdir( "per"+str( per_number ).zfill( 4 ) ):
        per_number += 1

    newper = "per" + str( per_number ).zfill( 4 )
    cmd = "mkdir " + newper
    subprocess.run( cmd, shell = True )

    return newper


def start_daq(args, newper):
    mada_config_path = args.c
    file_size = args.n
    run_control = args.s

    if int( file_size ) > MADADef.MADA_DEF_FILESIZE:
v        file_size = MADADef.MADA_DEF_FILESIZE
    print( f"data size per file: {file_size} Mbyte")

    # load config file
    MADAUtil.get_config( )
    with open( mada_config_path, 'r' ) as config_open :
        config_load = json.load( config_open )
    activeIP = []
    boardID = []
    for idx in config_load[ 'GBKB' ]:
        if config_load['GBKB'][idx]['active'] == 1:
            activeIP.append( config_load['GBKB'][idx]['IP'] )
            boardID.append( idx )
            print( config_load['GBKB'][idx]['IP'] )
    
    print( f"Number of GBKB boards: {len( activeIP )}/{MADADef.MAX_BOARDS}" )

    cmd = f"cp {mada_config_path} {newper}"
    proc = subprocess.run( cmd, shell = True )

    MADAUtil.kill_process( )

    # DAQ run
    fileperdir = 10000
    fileID = 0
    while fileID < fileperdir:
        print( fileID, "/", fileperdir )

        # send message to check LV here
        
        pids = []
        for i in range( len( activeIP ) ):
            IP = activeIP[i]
            filename_head = newper + "/" + boardID[i] + "_" + str( fileID ).zfill( 4 )
            filename_mada = f"{filename_head}.mada"
            cmd = f"{MADADef.CPP_MADA_IWAKI} -n {file_size} -f {filename_mada} -i {IP}"
            print( cmd )
            proc = subprocess.Popen( cmd, shell = True, stdout = PIPE, stderr = None )
            pids.append( proc.pid )

        starttime = time.time( )
        for i in range( len( activeIP ) ):
            IP = activeIP[i]
            filename_head = newper + "/" + boardID[i] + "_" + str( fileID ).zfill( 4 )
            filename_info = f"{filename_head}.info"
            print( f"board {IP} info was written in {filename_info}" )
            dict = { }
            for idx in config_load['GBKB']:
                if config_load['GBKB'][idx]['IP'] == IP:
                    dict.update( config_load['GBKB'][idx] )
                    dd = {"GBKB": dict}
                    dmes = { }
                    dmes['start'] = starttime
                    ddmes = {"runinfo": dmes}
                    dd.update( ddmes )
                    with open( filename_info, mode = 'wt', encoding = 'utf-8' ) as file:
                        json.dump( dd, file, ensure_ascii = False, indent = 2 )

        print( f"GIGAiwaki pids: {pids}" )
        print( f"working directory: {newper}" )
        print( f"started at: {starttime}" )

        # send message to start DAQ here

        running = 1
        while running:
            runs = 0
            for i in range( len( pids ) ):
                cmd = f"ps aux | awk \'$2=={pids[i]}\' | wc -l"
                pnum = ( subprocess.Popen( cmd, stdout=subprocess.PIPE,
                                           shell = True ).communicate( )[0]).decode( 'utf-8' )
                if int( pnum ) == 1:
                    runs += 1

            if runs < len( pids ):
                running = 0
                print( "file terminate" )
                endtime = time.time( )
                MADAUtil.kill_process( )
                break

        # send message to stop DAQ here

        print( f"file {fileID} finished at {endtime}" )
        realtime = endtime - starttime
        print( f"real time = {realtime}" )
        size = { bid: 0 for bid in MADADef.ALL_BOARDS }
        for i in range( len( activeIP ) ):
            filename_head = newper + "/" + boardID[i] + "_" + str( fileID ).zfill( 4 )
            filename_mada = f"{filename_head}.mada"
            filename_info = f"{filename_head}.info"
            cmd = f"ls -l {filename_mada}"
            proc = subprocess.Popen( cmd, stdout = subprocess.PIPE, shell = True ).communicate( )[0].decode( 'utf-8' )
            print( proc )
            sizel = str( proc ).split( )
            print( f"size= {sizel[4]} byte" )
            dmes = {}
            dmes['end'] = endtime
            dmes['size'] = sizel[4]
            size[boardID[i]] = sizel[4]
            ddmes = {"runinfo": dmes}
            info_open = open( filename_info, 'r' )
            info_load = json.load( info_open )
            dict_giga = {}
            dict_info = {}
            for x in info_load['GBKB']:
                dict_giga.update(info_load['GBKB'])
            for x in info_load['runinfo']:
                dict_info.update(info_load['runinfo'])
            dict_info.update( dmes )
            dict = {"GBKB": dict_giga, "runinfo": dict_info}
            with open( filename_info, mode='w', encoding='utf-8' ) as file:
                json.dump( dict, file, ensure_ascii = False, indent = 2 )

        y  = str( datetime.datetime.fromtimestamp( endtime ).year )
        m  = str( datetime.datetime.fromtimestamp( endtime ).month )
        d  = str( datetime.datetime.fromtimestamp( endtime ).day )
        ratefile = MADADef.DEF_RATEPATH + y + m.zfill( 2 ) + d.zfill( 2 )

        # write out event rate into text file
        with open(ratefile, 'a') as f:
            rate = {bid: 0 for bid in MADADef.ALL_BOARDS}
            for ii in range( len( activeIP ) ):
                rate[boardID[ii]] = float( size[boardID[ii]] ) / realtime
                f.write( f"{endtime}\t{size}\t{rate}\n" )

        # compensate size and rate dict when inactive board exist
        inactive_board = list( set( MADADef.ALL_BOARDS ) - set( boardID ) )
        for bid in inactive_board:
            size[bid] = 0
            rate[bid] = 0

        fileID += 1




def main():

    print( "**MADA start on MAQS servers**" )
    print( "**Micacle Argon DAQ (http://github.com/kobeDM/MADA)**" )
    print( "**2025 Aug by S. Higashino**" )

    parser = argparse.ArgumentParser( )
    parser.add_argument( "-c", help = "config file name", default = MADADef.DEF_CONFIGFILE )
    parser.add_argument( "-s", help = "silent mode (control only)", action = 'store_true' )
    parser.add_argument( "-n", help = "file size in MB", default = MADADef.DEF_FILESIZE )

    args = parser.parse_args()
    current_period = make_new_period()
    
    try:
        start_daq(args, current_period)
    except KeyboardInterrupt:
        print()
        print("===========================")
        print("aborted DAQ")
        print("===========================")

        # send message to stop DAQ (DAQ enable control) here
        MADAUtil.kill_DAQ( args.c, current_period )
    
if __name__ == "__main__":
    main( )
