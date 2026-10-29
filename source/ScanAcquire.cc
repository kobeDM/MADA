#include "../include/RBCP.h"
#include "../include/SiTCP.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <iostream>
#include <string>
#include <unistd.h>
#include <vector>

using namespace std;
using Clock = chrono::steady_clock;

namespace
{
    const int    kChannels   = 128;
    const int    kDacMax     = 63;
    const int    kVthMax     = 0x3fff;
    const size_t kMaxBytes   = 0x1000000;  // bytes kept per point
    const int    kReadWaitMs = 200;        // wait for data in one read

    struct Options {
            string ip;
            string mode;
            string outdir;
            int    start   = 0;
            int    end     = 0;
            int    step    = 1;
            int    vth     = -1;  // dac mode: fixed Vth
            string dacfile;       // vth mode: DAC values written before the scan
            long   events  = 500;
            double timeout = 15;  // sec per point
            double settle  = 1;   // sec between a setting and the first data
    };

    void Usage( )
    {
        cerr << " USAGE> ScanAcquire [IP] vth [out dir.] [start Vth] [end Vth] [step] -d [DAC file] [options]" << endl;
        cerr << "        ScanAcquire [IP] dac [out dir.] [start DAC] [end DAC] [step] -v [Vth] [options]" << endl;
        cerr << "   Vth: 0 to 16383, DAC: 0 to 63 (the same value on all channels in the dac mode)" << endl;
        cerr << "   -n [events per point]  default 500" << endl;
        cerr << "   -t [timeout sec per point]  default 15; a point that times out keeps the events it got" << endl;
        cerr << "   -s [settle sec after a setting]  default 1" << endl;
        cerr << " Writes scan_config.out, scan_points.csv and one data file per point into the out dir." << endl;
    }

    bool Parse( int argc, char *argv[], Options &o )
    {
        if ( argc < 7 )
            return false;
        o.ip     = argv[1];
        o.mode   = argv[2];
        o.outdir = argv[3];
        o.start  = atoi( argv[4] );
        o.end    = atoi( argv[5] );
        o.step   = atoi( argv[6] );
        for ( int i = 7; i < argc; i += 2 ) {
            string key = argv[i];
            if ( i + 1 >= argc )
                return false;
            if ( key == "-d" )
                o.dacfile = argv[i + 1];
            else if ( key == "-v" )
                o.vth = atoi( argv[i + 1] );
            else if ( key == "-n" )
                o.events = atol( argv[i + 1] );
            else if ( key == "-t" )
                o.timeout = atof( argv[i + 1] );
            else if ( key == "-s" )
                o.settle = atof( argv[i + 1] );
            else
                return false;
        }

        int max = o.mode == "vth" ? kVthMax : kDacMax;
        if ( o.mode != "vth" && o.mode != "dac" )
            return false;
        if ( o.step <= 0 || o.start < 0 || o.end < o.start || o.end > max || o.events <= 0 || o.timeout <= 0 || o.settle < 0 )
            return false;
        if ( o.mode == "vth" && o.dacfile.empty( ) )
            return false;
        if ( o.mode == "dac" && ( o.vth < 0 || o.vth > kVthMax ) )
            return false;
        return true;
    }

    void WriteVth( RBCP &ctrl, int vth )
    {
        char cmd[2];
        cmd[0] = ( vth >> 8 ) & 0x3f;
        cmd[1] = vth & 0xff;
        ctrl.WriteRBCP( 0x80, cmd, 2 );
        cmd[0] = 0x01;
        ctrl.WriteRBCP( 0xf0, cmd, 1 );
    }

    void WriteDac( RBCP &ctrl, const vector<int> &dac )
    {
        char cmd[kChannels];
        for ( int ch = 0; ch < kChannels; ch++ )
            cmd[ch] = ctrl.convDAC( dac[ch], 0, 0 );
        ctrl.WriteRBCP( 0, cmd, kChannels );
        cmd[0] = 0x02;
        ctrl.WriteRBCP( 0xf0, cmd, 1 );
    }

    bool ReadDacFile( const string &name, vector<int> &dac )
    {
        ifstream f( name.c_str( ) );
        if ( !f )
            return false;
        dac.assign( kChannels, -1 );
        for ( int i = 0; i < kChannels; i++ ) {
            int ch, val;
            if ( !( f >> ch >> val ) || ch < 0 || ch >= kChannels || val < 0 || val > kDacMax )
                return false;
            dac[ch] = val;
        }
        for ( int v : dac )
            if ( v < 0 )
                return false;
        return true;
    }

    // Reads and drops data for the given time, so that no event taken before
    // the new setting is left in the buffers.
    void Flush( SiTCP &data, double seconds )
    {
        char buf[4096];
        auto t0 = Clock::now( );
        while ( chrono::duration<double>( Clock::now( ) - t0 ).count( ) < seconds )
            data.ReadTimeout( buf, 50 );
    }

    struct Point {
            long   events  = 0;
            size_t bytes   = 0;
            double seconds = 0;
            string status;
    };

    // Collects events until the count, the time limit or the size limit is reached.
    Point Collect( SiTCP &data, const Options &o, const string &filename )
    {
        Point          p;
        ofstream       out( filename.c_str( ), ios::out | ios::binary );
        char           buf[4096];
        unsigned       window = 0;  // last 4 bytes
        auto           t0     = Clock::now( );
        bool           closed = false;
        while ( p.events < o.events && p.bytes < kMaxBytes ) {
            p.seconds = chrono::duration<double>( Clock::now( ) - t0 ).count( );
            if ( p.seconds > o.timeout )
                break;
            int num = data.ReadTimeout( buf, kReadWaitMs );
            if ( num == 0 ) {
                closed = true;
                break;
            }
            if ( num < 0 )
                continue;

            out.write( buf, num );
            p.bytes += num;
            for ( int i = 0; i < num; i++ ) {
                window = ( window << 8 ) | (unsigned char)buf[i];
                if ( window == 0x75504943 )  // "uPIC": footer of an event
                    p.events++;
            }
        }
        p.seconds = chrono::duration<double>( Clock::now( ) - t0 ).count( );
        out.close( );
        p.status = closed ? "closed" : ( p.events >= o.events ? "ok" : "timeout" );
        return p;
    }
}  // namespace

int main( int argc, char *argv[] )
{
    Options o;
    if ( !Parse( argc, argv, o ) ) {
        Usage( );
        return 1;
    }

    vector<int> dac;
    if ( o.mode == "vth" && !ReadDacFile( o.dacfile, dac ) ) {
        cerr << " ERROR: cannot read 128 channels of DAC values (0 to 63) from " << o.dacfile << endl;
        return 1;
    }

    string cmd_mkdir = "mkdir -p " + o.outdir;
    if ( system( cmd_mkdir.c_str( ) ) != 0 ) {
        cerr << " ERROR: cannot create " << o.outdir << endl;
        return 1;
    }

    ofstream cfg( ( o.outdir + "/scan_config.out" ).c_str( ) );
    cfg << "IP: " << o.ip << endl;
    cfg << "Mode: " << o.mode << endl;
    cfg << "Start: " << o.start << endl;
    cfg << "End: " << o.end << endl;
    cfg << "Step: " << o.step << endl;
    cfg << "Events: " << o.events << endl;
    cfg << "Timeout: " << o.timeout << endl;
    cfg << "Settle: " << o.settle << endl;
    if ( o.mode == "vth" )
        cfg << "DACfile: " << o.dacfile << endl;
    else
        cfg << "Vth: " << o.vth << endl;
    cfg << "Time: " << time( NULL ) << endl;
    cfg.close( );

    RBCP  ctrl;
    SiTCP data;
    if ( ctrl.Open( o.ip ) || data.Open( o.ip ) ) {
        cerr << " ERROR: cannot open " << o.ip << endl;
        return 1;
    }

    if ( o.mode == "vth" ) {
        WriteDac( ctrl, dac );
    } else {
        WriteVth( ctrl, o.vth );
    }
    sleep( (unsigned)( o.settle + 0.999 ) );

    ofstream points( ( o.outdir + "/scan_points.csv" ).c_str( ) );
    points << "value,file,events,bytes,seconds,status" << endl;

    int good = 0, total = 0;
    for ( int v = o.start; v <= o.end; v += o.step ) {
        if ( o.mode == "vth" )
            WriteVth( ctrl, v );
        else
            WriteDac( ctrl, vector<int>( kChannels, v ) );

        Flush( data, o.settle );

        char name[64];
        snprintf( name, sizeof( name ), "%s_%05d.scn", o.mode.c_str( ), v );
        Point p = Collect( data, o, o.outdir + "/" + name );

        points << v << ',' << name << ',' << p.events << ',' << p.bytes << ',' << p.seconds << ',' << p.status << endl;
        points.flush( );
        cout << " " << o.mode << " " << v << ": " << p.events << " events, " << p.seconds << " s, " << p.status << endl;
        total++;
        if ( p.events > 0 )
            good++;
        if ( p.status == "closed" ) {
            cerr << " ERROR: the board closed the data connection" << endl;
            return 2;
        }
    }

    if ( good == 0 ) {
        cerr << " ERROR: no event arrived at any of the " << total << " points; check the trigger input and the board" << endl;
        return 3;
    }
    if ( good < total )
        cerr << " WARNING: " << total - good << " of " << total << " points got no event" << endl;
    return 0;
}
