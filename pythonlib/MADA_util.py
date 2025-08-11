import os
import time
import json
import subprocess
from subprocess import PIPE
import MADA_defs as MADADef


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
        

def kill_process( ):
    modules = [ 'MADA_iwaki' ]
    killpids = []
    for i in range( len( modules ) ):
        print( modules[i] )
        ps = f"ps -aux  | grep -v \' grep \' | grep {modules[i]}"
        process = ( subprocess.Popen( ps, stdout = subprocess.PIPE, shell = True ).communicate( )[0] ).decode( 'utf-8' )
        pl = process.split( "\n" )
        for j in range( len( pl ) - 1 ):
            pll = pl[j].split( )
            killpids.append( pll[1] )

    for i in range( len( killpids ) - 1 ):
        kill = f"kill -KILL {killpids[i]}"
        subprocess.run( kill, shell = True )
    
    return


def kill_DAQ( config, pername ):
    if per[0] != "p":
        pername = "per"+str(per).zfill(4)

    print( "**MADAkiller.py**" )
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

    fileID = 0
    target_file = pername + "/*_" + str( fileID ).zfill( 4 ) + ".info"
    while len( glob.glob( target_file ) ):
        fileID = fileID + 1
        target_file = per + "/*_" + str( fileID ).zfill( 4 ) + ".info"
    fileID = fileID - 1
    target_file = per + "/*_" + str( fileID ).zfill( 4 ) + ".info"
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
