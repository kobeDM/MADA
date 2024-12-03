#! /usr/bin/env python3

import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import datetime

from influxdb import InfluxDBClient

HOME=os.environ["HOME"]
RATEPATH=HOME+"/rate/"

class ScalerLoggingEventHandler( LoggingEventHandler ):
    def on_modified( self, event ):

        if event.is_directory == False:
            target_filepath = event.src_path
            with open( target_filepath, "r" ) as f:
                last_line = f.readlines()[-1]

            dt = last_line.split()[0]
            startunixtime = float( last_line.split( )[ 1 ] )
            endunixtime = float( last_line.split( )[ 2 ] )
            filesize_cathode = float( last_line.split( )[ 3 ] )
            filesize_anode = float( last_line.split( )[ 4 ] )
            realrate_cathode = float( last_line.split( )[ 5 ] )
            realrate_anode = float( last_line.split( )[ 6 ] )
            scalertime = datetime.datetime.utcnow()
            print( "cathode real rate: " + str(realrate_cathode) + ", anode real rate: " + str(realrate_anode) )
            # print( scalertime )
            json_data = [
                {
                    'measurement' : 'scaler',
                    'fields' : {
                        'trigger_rate_real_anode' : realrate_anode,
                        'trigger_rate_real_cathode' : realrate_cathode,
                    },
                    'time' : scalertime,
                    'tags' : {
                        'host' : 'na8',
                        'device' : 'na8',
                    }
                }
            ]
            result = client.write_points( json_data )    

def main():
    client = InfluxDBClient( host = "10.37.0.216",
                             port = "8086",
                             username = "root",
                             password = "root",
                             database = "cn1")

    logging.basicConfig( level = logging.INFO,
                         format = '%(asctime)s - %(message)s',
                         datefmt = '%Y-%m-%d %H:%M:%S' )
    path = RATEPATH
    event_handler = ScalerLoggingEventHandler( )
    observer = Observer( )
    observer.schedule( event_handler, path, recursive = True )
    observer.start( )
    try:
        while True:
            time.sleep( 1 )
    except KeyboardInterrupt:
        observer.stop( )
        
    observer.join( )
        
if __name__ == "__main__":
    main()