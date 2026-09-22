#include "../include/RBCP.h"
#include "../include/SiTCP.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <getopt.h>
#include <iomanip>
#include <iostream>
#include <signal.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

using namespace std;

int GetBottomRow( )
{
    struct winsize w;
    ioctl( STDOUT_FILENO, TIOCGWINSZ, &w );
    return w.ws_row;
}

int main( int argc, char *argv[] )
{
    bool end_flag   = 0;
    int  numperfile = 1000;

    string filename;
    string IP;

    ofstream OutData;

    struct option longopts[] = {
        {"help",      no_argument,       NULL, 'h'},
        {"numperdir", required_argument, NULL, 'n'},
        {"filename",  required_argument, NULL, 'f'},
        {"IP",        required_argument, NULL, 'i'},
        {0,           0,                 0,    0  },
    };

    int opt, longindex;
    int hopt = 0;

    while ( ( opt = getopt_long( argc, argv, "hn:f:i:", longopts, &longindex ) ) != -1 ) {
        switch ( opt ) {
        case 'h':
            hopt = 1;
            break;

        case 'n':
            numperfile = atoi( optarg );
            break;

        case 'i':
            IP = optarg;
            break;

        case 'f':
            filename = optarg;
            break;
        }
    }

    if ( hopt ) {
        printf( "MADA [-h] [-n num_of_events] [-f filename] [-i IP]\n" );
        return 0;
    }

    SiTCP EtherDAQ( IP );
    OutData.open( filename, ios::out | ios::binary );

    cout << "Datafile " << filename << endl;
    cout << "IP: " << IP << endl;

    char tmp_data[4096];
    int  num        = 0;
    int  trig_count = 0;
    int  max_trig   = numperfile;

    char c_data[4096];

    while ( !end_flag ) {
        num = EtherDAQ.Read( c_data );

        if ( num == 0 ) {
            cerr << "ERROR: connection closed by Iwaki board" << endl;
            OutData.close( );
            exit( EXIT_FAILURE );
        }

        if ( num < 0 ) {
            cerr << "ERROR: failed to read from Iwaki board" << endl;
            OutData.close( );
            exit( EXIT_FAILURE );
        }

        OutData.write( c_data, num );
        OutData.flush( );

        if ( num > 4096 ) {
            cout << "warning: data overflow..." << endl;
            continue;
        }

        // detect footer pattern "uPIC"
        for ( int i = 0; i < num - 3; ++i ) {
            if ( c_data[i] == 'u' && c_data[i + 1] == 'P' && c_data[i + 2] == 'I' && c_data[i + 3] == 'C' ) {
                trig_count++;
            }
        }

        cout << setw( 6 ) << trig_count << "/" << setw( 6 ) << max_trig << " events stored\r" << flush;

        if ( trig_count >= max_trig ) {
            cout << endl;
            OutData.close( );
            end_flag = 1;
        }
    }

    return 0;
}