import os
import time
import subprocess
import glob
import json
import datetime
from subprocess import PIPE
import MADA_defs as MADADef


def get_current_period() -> str:
    per_number = 0
    while os.path.isdir( "per"+str( per_number ).zfill( 4 ) ):
        per_number += 1

    current_per = "per" + str( per_number - 1 ).zfill( 4 )
    return current_per


def make_new_period( ) -> str:
    per_number = 0
    while os.path.isdir( "per"+str( per_number ).zfill( 4 ) ):
        per_number += 1

    newper = "per" + str( per_number ).zfill( 4 )
    cmd = "mkdir " + newper
    subprocess.run( cmd, shell = True )

    return newper


def make_new_scan_run( scan_header ) -> str:
    new_scan_run = ""
    files = glob.glob( scan_header + "*" )
    if len( files ) == 0:
        new_scan_run = scan_header + "0".zfill( 4 )
    else:
        files.sort( reverse = True )
        num_pos = files[0].find( "run" )
        new_scan_run = scan_header + str( int( files[0][num_pos+3:num_pos+3+4] ) + 1 ).zfill( 4 )

    return new_scan_run
    

def get_config( ):
    if os.path.isfile( MADADef.DEF_CONFIGFILE ):
        print( MADADef.DEF_CONFIGFILE +" exists." )
    else:
        # make config file from skelton file
        CONFIG_SKEL = f"{MADADef.MADA_ENV_PATH}/config/{MADADef.DEF_CONFIG_SKEL_FILE}"
        print( f"\tMADA config slkelton file: {CONFIG_SKEL}" )

        cmd = f"cp {CONFIG_SKEL} {MADADef.DEF_CONFIGFILE}"
        proc = subprocess.run( cmd, shell=True, stdout=PIPE, stderr=None, check=False, capture_output=False)

    return
        

def kill_process( procname ):
    killpids = []
    ps = f"ps -aux  | grep -v \' grep \' | grep {procname}"
    process = ( subprocess.Popen( ps, stdout = subprocess.PIPE, shell = True ).communicate( )[0] ).decode( 'utf-8' )
    pl = process.split( "\n" )
    for j in range( len( pl ) - 1 ): # range( len( ) - 1 ) is necessary to avoid "grep" process itself
        pll = pl[j].split( )
        killpids.append( pll[1] )
        print( f"listing {pl[j]}" )

    for i in range( len( killpids ) ):
        kill = f"kill -KILL {killpids[i]}"
        subprocess.run( kill, shell = True )
        print( f"process: {killpids[i]} killed." )
    
    return

def kill_DAQ( config, pername ):

    print( f"target dir: {pername}" )

    # load config file
    config_open = open( config, 'r' )
    config_load = json.load( config_open )
    activeIP = []
    boardID = []
    for idx in config_load['GBKB']:
        if config_load['GBKB'][idx]['active'] == 1:
            activeIP.append( config_load['GBKB'][idx]['IP'] )
            boardID.append( idx )

    endtime = time.time()

    kill_process( 'MADA_iwaki' )
    
    fileID = 0
    target_file = pername + "/*_" + str( fileID ).zfill( 4 ) + ".info"
    print( f"target file: {target_file}" )

    size = { bid: 0 for bid in MADADef.ALL_BOARDS }
    for i in range(len(activeIP)):
        filename_head = pername + "/" + boardID[i] + "_" + str( fileID ).zfill( 4 )
        filename_mada = f"{filename_head}.mada"
        filename_info = f"{filename_head}.info"
        cmd = f"ls -l {filename_mada}"
        proc = subprocess.Popen( cmd, stdout = subprocess.PIPE, shell = True ).communicate( )[0].decode( 'utf-8' )
        sizel = str( proc ).split( )
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
        starttime = dict_info["start"]
        dict_info.update(dmes)
        dict = {"GBKB": dict_giga, "runinfo": dict_info}
        with open( filename_info, mode='w', encoding='utf-8' ) as file:
            json.dump( dict, file, ensure_ascii = False, indent = 2 )

        realtime = endtime - starttime
        y = str( datetime.datetime.fromtimestamp( endtime ).year )
        m = str( datetime.datetime.fromtimestamp( endtime ).month )
        d = str( datetime.datetime.fromtimestamp( endtime ).day )
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
