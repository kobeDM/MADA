#! /usr/bin/python3
import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import datetime
from influxdb import InfluxDBClient
import MADA_defs as MADADef


client = InfluxDBClient( host = "10.37.0.214",
                         port = "8086",
                         username = "root",
                         password = "root",
                         database = "miraclue")
   

# code inherited from MAZYSCA_SW
class RateLoggingEventHandler( LoggingEventHandler ):
    def on_modified( self, event ):

        if event.is_directory == False:
            target_filepath = event.src_path
            if (str)(target_filepath).find( "per" ) == False:
                return
            
            with open( target_filepath, "r" ) as f:
                last_line = f.readlines()[-1]

            fileID = last_line.split()[0]
            realtimeClk_str = last_line.split( )[ 1 ]
            livetimeClk_str = last_line.split( )[ 2 ]
            realtimeClk = int(realtimeClk_str)
            livetimeClk = int(livetimeClk_str)
            if realtimeClk < 1 or livetimeClk < 1:
                print( "realtime or livetime is zero. skip event rate logging." )
                return
            
            realtime = float( realtimeClk ) / 10.0 * 1e-3 # scaler clock: 10kHz
            livetime = float( livetimeClk ) / 10.0 * 1e-3 # scaler clock: 10kHz
            num_trigger = float( last_line.split( )[ 3 ] )
            unixtime = float( last_line.split( )[ 4 ] )
            trigger_rate_real = num_trigger / realtime
            trigger_rate_live = num_trigger / livetime
            scalertime = datetime.datetime.utcnow()
            print( "real rate: " + str(trigger_rate_real) + ", live rate: " + str(trigger_rate_live) )
            print( scalertime )
            json_data = [
                {
                    'measurement' : 'scaler',
                    'fields' : {
                        'trigger_rate_real' : trigger_rate_real,
                        'trigger_rate_live' : trigger_rate_live,
                    },
                    'time' : scalertime,
                    'tags' : {
                        'host' : 'mascot',
                        'device' : 'macaron',
                    }
                }
            ]
            result = client.write_points( json_data )    

def main( ):
    logging.basicConfig( level = logging.INFO,
                         format = '%(asctime)s - %(message)s',
                         datefmt = '%Y-%m-%d %H:%M:%S' )
    path = sys.argv[1] if len( sys.argv ) > 1 else '.'
    event_handler = RateLoggingEventHandler( )
    observer = Observer( )
    observer.schedule( event_handler, path, recursive = True )
    observer.start( )
    try:
        while True:
            time.sleep( 1 )
    except KeyboardInterrupt:
        observer.stop( )
        
    observer.join( )

    return

            
if __name__ == "__main__":
    main( )
