#! /usr/bin/python3
import os
import time
import json
import glob
from subprocess import PIPE
from datetime import datetime, timedelta, timezone
from influxdb import InfluxDBClient
import MADA_defs as MADADef

   
def send_command( dev, command, delay = 0.1, read_len=256 ):
    lock_file = os.path.baseename( dev )
    lock_filepath = f"{MADADef.LOCK_TMP_PATH}/{MADADef.LOCK_FILENAME_ACCESS_PREFIX}_{lock_file}"
    while True:
        if os.path.isfile( lock_filepath ) == True:
            time.sleep( 0.1 )
            continue
        else:
            break

    cmd = f"touch {lock_filepath}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
    with open( dev, "r+b", buffering = 0 ) as f:
        f.write( command.encode( "ascii" ) )
        time.sleep( delay )
        if "?" in command:
            retVal = f.read( read_len ).decode( "ascii", errors = "ignore" )

    cmd = f"rm {lock_filepath}"
    proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
    proc.communicate( )
            
    return retVal

    
def load_json( json_file = MADADef.DEF_LV_CONFIGFILE ):
    with open( json_file, "r" ) as conf:
        return json.load( conf )

    
def sort_devices( dev_file, config ):
    print( "Sorting PWR401Ls by S/N." )
    print( "Device files are: " + dev_file )
    ser_num = config["devices"]["serialnumber"]
    usbtmc_list = glob.glob( dev_file )
    print( "Before: " )
    print( usbtmc_list )
    dev_list = ["N/A"] * len( ser_num )
    for i in range( len( usbtmc_list ) ):
        dev_info = send_command( usbtmc_list[i], MADADef.LV_QUERY_ASK_SERIAL )
        ser_num_info = dev_info.split( "," )[2]
        if ser_num_info == ser_num[0]:
            dev_list[0] = usbtmc_list[i]
        elif ser_num_info == ser_num[1]:
            dev_list[1] = usbtmc_list[i]
        elif ser_num_info == ser_num[2]:
            dev_list[2] = usbtmc_list[i]
        else:
            continue
    print( "After: " )
    print( dev_list )
    time.sleep( 1 )
    return dev_list


def output_on( dev_list, config ):
    print( "Output ON." )
    volt_set = config["devices"]["voltage"]
    for ch in range( len( dev_list ) ):
        cmd_volt = f"{MADADef.LV_QUERY_SET_VOLTAGE} {volt_set[ch]}"
        send_command( dev_list[ch], cmd_volt )
        send_command( dev_list[ch], MADADef.LV_QUERY_OUTPUT_ON )
        print( f"CH{ch} is set to {volt_set[ch]} V." )
    time.sleep( 1 )


 def monitor_value( dev_list, config ):
    print( "Monitoring Start." )
    curr_lim = config["devices"]["currentlimit"]
    measurement = config["influxdb"]["measurement"]
    host_tags = config["influxdb"]["tags"]["host"]
    device_tags = config["influxdb"]["tags"]["device"]
    itv_mon = config["interval"]["monitor"]
    itv_rbt = config["interval"]["reboot"]
    itv_db = config["interval"]["database"]
    client = InfluxDBClient(
        host = config["influxdb"]["host"],
        port = config["influxdb"]["port"],
        username = config["influxdb"]["username"],
        password = config["influxdb"]["password"],
        database = config["influxdb"]["database"]
    )
    loop_num = 0
    try:
        while True:
            curr_meas = []
            volt_meas = []
            for ch in range( len( dev_list ) ):
                curr_val = send_command( dev_list[ch], MADADef.LV_QUERY_GET_CURRENT )
                curr_meas.append( float( curr_val.strip( ) ) )
                volt_val = send_command( dev_list[ch], MADADef.LV_QUERY_GET_VOLTAGE )
                volt_meas.append( float( volt_val.strip( ) ) )

            #current check
            if os.path.isfile( MADADef.LOCK_FILE_FULLPATH_AUTORESET ) == False:
                if curr_meas[1] > curr_lim[1] or curr_meas[2] > curr_lim[2]:
                    print( "+/- 2.5 V reset." )
                    send_command( dev_list[1], MADADef.LV_QUERY_OUTPUT_OFF )
                    send_comnnmand( dev_list[2], MADADef.LV_QUERY_OUTPUT_OFF )
                    time.sleep( itv_rbt )
                    send_command( dev_list[1], MADADef.LV_QUERY_OUTPUT_ON )
                    send_command( dev_list[2], MADADef.LV_QUERY_OUTPUT_ON )
                if curr_meas[0] > curr_lim[0]:
                    print( "+3.3 V resetn." )
                    send_command( dev_list[0], MADADef.LV_QUERY_OUTPUT_OFF )
                    time.sleep( itv_rbt )
                    send_command( dev_list[0], MADADef.LV_QUERY_OUTPUT_ON )

            #influxdb
            utc = datetime.utcnow( )
            jst = datetime.now( timezone( timedelta( hours = 9 ) ) )
            print( jst.strftime( "%Y-%m-%d %H:%M:%S %Z" ) )
            print( volt_meas, curr_meas )
            if loop_num % itv_db == 0:
                json_data = [
                    {
                        "measurement": measurement,
                        "fields": {
                            "CH0_I": curr_meas[0],
                            "CH0_V": volt_meas[0],
                            "CH1_I": curr_meas[1],
                            "CH1_V": volt_meas[1],
                            "CH2_I": curr_meas[2],
                            "CH2_V": volt_meas[2]
                        },
                        "time": utc,
                        "tags": {
                            "host": host_tags,
                            "device": device_tags
                        }
                    }
                ]
                client.write_points( json_data )
                print( "Data was sent to influxDB." )
            loop_num += 1
            time.sleep( itv_mon )

    except KeyboardInterrupt:
        for ch in range( len( dev_list ) ):
            send_command( dev_list[ch], MADADef.LV_QUERY_OUTPUT_OFF )
        print( f"\n Output OFF." )

    return
        
def main( ):

    if os.path.isfile( MADADef.DEF_LV_CONFIGFILE ) == False:
        cmd = f"cp {MADA_ENV_PATH}/config/{DEF_LV_CONFIGFILE}"
        proc = subprocess.Popen( cmd, shell=True, stdout=PIPE, stderr=None )
        proc.communicate( )
        if proc.returncode == 0:
            print( f"{DEF_LV_CONFIGFILE} copied from MADA repository" )
        else:
            print( f"Failed to copy {DEF_LV_CONFIGFILE} from MADA repository" )
            return
        
    config = load_json( MADADef.DEF_LV_CONFIGFILE )
    dev_file = MADADef.DEF_LV_USBDEVFILE
    dev_list = sort_devices( dev_file, config )
    output_on( dev_list, config )
    monitor_value( dev_list, config )

        
if __name__ == "__main__":
    main( )
