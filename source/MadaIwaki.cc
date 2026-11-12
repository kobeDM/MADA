#include "../include/RBCP.h"
#include "../include/SiTCP.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <getopt.h>
#include <iomanip>
#include <iostream>
#include <cerrno>
#include <signal.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

using namespace std;

// Timing diagnostics: stalls are reported on stderr as one line each, with the
// wall-clock time (epoch s) so they can be matched with the .mada events:
//   WARNING t=... kind=write_slow sec=... events=...
//     writing and flushing the data to disk took sec (PC side)
// A board that lags behind the other boards is detected by the DAQ script
// (kind=board_lag), which sees all the boards; one reader cannot tell a missing
// trigger from a stalled board.
using SteadyClock = std::chrono::steady_clock;

double EpochNow( )
{
    return std::chrono::duration<double>( std::chrono::system_clock::now( ).time_since_epoch( ) ).count( );
}

double Seconds( SteadyClock::time_point from, SteadyClock::time_point to )
{
    return std::chrono::duration<double>( to - from ).count( );
}

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
        {"warn-sec",  required_argument, NULL, 't'},
        {0,           0,                 0,    0  },
    };

    double warn_sec = 0.2;  // s, a disk write longer than this is reported

    int opt, longindex;
    int hopt = 0;

    while ( ( opt = getopt_long( argc, argv, "hn:f:i:t:", longopts, &longindex ) ) != -1 ) {
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

        case 't':
            warn_sec = atof( optarg );
            break;

        case 'f':
            filename = optarg;
            break;
        }
    }

    if ( hopt ) {
        printf( "MADA [-h] [-n num_of_events] [-f filename] [-i IP] [-t warn_sec]\n" );
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

    const int      max_warnings    = 1000;  // keep a pathological run from flooding the log
    int            warnings        = 0;
    double         max_recv_wait   = 0.0;
    double         max_write       = 0.0;

    while ( !end_flag ) {
        auto recv_start = SteadyClock::now( );
        num             = EtherDAQ.Read( c_data );
        auto recv_end   = SteadyClock::now( );

        const double recv_wait = Seconds( recv_start, recv_end );
        if ( num > 0 && recv_wait > max_recv_wait )
            max_recv_wait = recv_wait;

        if ( num == 0 ) {
            cerr << "ERROR: connection closed by Iwaki board" << endl;
            OutData.close( );
            exit( EXIT_FAILURE );
        }

        if ( num < 0 ) {
            cerr << "ERROR: failed to read from Iwaki board (errno=" << errno << " " << strerror( errno ) << ")" << endl;
            OutData.close( );
            exit( EXIT_FAILURE );
        }

        auto write_start = SteadyClock::now( );
        OutData.write( c_data, num );
        OutData.flush( );
        const double write_time = Seconds( write_start, SteadyClock::now( ) );
        if ( write_time > max_write )
            max_write = write_time;
        if ( write_time > warn_sec && warnings < max_warnings ) {
            warnings++;
            fprintf( stderr, "WARNING t=%.3f kind=write_slow sec=%.3f events=%d\n", EpochNow( ), write_time, trig_count );
        }

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
            fprintf( stderr, "INFO t=%.3f kind=summary events=%d warnings=%d max_recv_wait=%.3f max_write=%.3f\n",
                     EpochNow( ), trig_count, warnings, max_recv_wait, max_write );
        }
    }

    return 0;
}