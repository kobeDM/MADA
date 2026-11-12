#include "../include/AdalmUtil.h"
#include "../include/SciPulse.h"

#include <TFile.h>
#include <TNamed.h>
#include <TTree.h>

#include <libm2k/analog/m2kanalogin.hpp>
#include <libm2k/m2khardwaretrigger.hpp>

#include <atomic>
#include <cmath>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <random>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

using namespace std;

namespace
{
    const double kSampleRate    = 100e6;  // Hz, the maximum of the ADALM2000
    const double kTriggerWindow = 200;    // ns around the expected position in which the trigger edge is looked for
    const double kSaturation    = 0.98;   // fraction of the range from which a sample counts as saturated
    const int    kReadTimeoutMs = 1000;   // ms to wait for a buffer before looking at the stop flag
    const int    kSaveEvery     = 500;    // triggers between two saves of the tree

    // flags of a trigger
    const int kNoTriggerEdge = 1;  // the DAQ trigger edge was not found near its expected place
    const int kSaturated     = 2;  // a sample reached the range limit

    atomic<bool> g_stop( false );

    void OnSignal( int ) { g_stop = true; }

    struct Channel {
            int    index;      // 0 or 1
            double threshold;  // V
            bool   falling;
    };

    struct Options {
            string serial;
            string output;
            Channel pmt     = { 0, -0.4, true };
            Channel trigger = { 1, -0.4, true };
            bool   high_range = false;
            int    buffer     = 8192;
            int    pre        = 8000;
            bool   waveform   = false;
            bool   simulate   = false;
            double sim_rate   = 50;  // Hz, triggers of the simulation
    };

    void Usage( )
    {
        cerr << " USAGE> AdalmAnalogIn -s [serial] -o [out.root] [options]" << endl;
        cerr << "   -p [ch] [V] [rising|falling]   PMT channel (1 or 2), threshold, edge (default 1 -0.4 falling)" << endl;
        cerr << "   -t [ch] [V] [rising|falling]   DAQ trigger channel, threshold, edge (default 2 -0.4 falling)" << endl;
        cerr << "   -r [low|high]                  input range +-2.5 V or +-25 V (default low)" << endl;
        cerr << "   -b [samples]                   samples per buffer, a multiple of 4 (default 8192)" << endl;
        cerr << "   -e [samples]                   samples before the trigger, at most 8192 (default 8000)" << endl;
        cerr << "   -w                             also store the waveforms" << endl;
        cerr << "   --simulate [Hz]                no ADALM: simulated signals at this trigger rate (for tests)" << endl;
        cerr << " Stops on SIGTERM/SIGINT. Writes the tree 'trigger' (one entry per buffer), the object 'meta'," << endl;
        cerr << " [out].info and, every second, [out].status. Prints READY when the acquisition is armed." << endl;
    }

    bool ParseChannel( int &i, int argc, char *argv[], Channel &c )
    {
        if ( i + 3 >= argc )
            return false;
        int ch = atoi( argv[i + 1] );
        if ( ch != 1 && ch != 2 )
            return false;
        c.index     = ch - 1;
        c.threshold = atof( argv[i + 2] );
        string edge = argv[i + 3];
        if ( edge != "falling" && edge != "rising" )
            return false;
        c.falling = edge == "falling";
        i += 3;
        return true;
    }

    bool ParseOptions( int argc, char *argv[], Options &o )
    {
        for ( int i = 1; i < argc; i++ ) {
            string key = argv[i];
            if ( key == "-s" && i + 1 < argc )
                o.serial = argv[++i];
            else if ( key == "-o" && i + 1 < argc )
                o.output = argv[++i];
            else if ( key == "-p" ) {
                if ( !ParseChannel( i, argc, argv, o.pmt ) )
                    return false;
            } else if ( key == "-t" ) {
                if ( !ParseChannel( i, argc, argv, o.trigger ) )
                    return false;
            } else if ( key == "-r" && i + 1 < argc ) {
                string r = argv[++i];
                if ( r != "low" && r != "high" )
                    return false;
                o.high_range = r == "high";
            } else if ( key == "-b" && i + 1 < argc )
                o.buffer = atoi( argv[++i] );
            else if ( key == "-e" && i + 1 < argc )
                o.pre = atoi( argv[++i] );
            else if ( key == "-w" )
                o.waveform = true;
            else if ( key == "--simulate" && i + 1 < argc ) {
                o.simulate = true;
                o.sim_rate = atof( argv[++i] );
            } else
                return false;
        }

        if ( o.output.empty( ) || ( o.serial.empty( ) && !o.simulate ) )
            return false;
        if ( o.pmt.index == o.trigger.index )
            return false;
        if ( o.buffer < 32 || o.buffer % 4 != 0 || o.pre < 1 || o.pre > 8192 || o.pre + 100 > o.buffer )
            return false;
        return o.sim_rate > 0;
    }

    double Now( )
    {
        using namespace chrono;
        return duration<double>( system_clock::now( ).time_since_epoch( ) ).count( );
    }

    // Replace the extension of the output name.
    string WithSuffix( const string &output, const string &suffix )
    {
        size_t dot = output.rfind( ".root" );
        return ( dot == string::npos ? output : output.substr( 0, dot ) ) + suffix;
    }

    void WriteStatus( const string &path, long triggers, double last_epoch )
    {
        string tmp = path + ".tmp";
        {
            ofstream f( tmp.c_str( ) );
            f << fixed << setprecision( 3 );
            f << "triggers " << triggers << endl;
            f << "last_epoch " << last_epoch << endl;
            f << "time " << Now( ) << endl;
        }
        rename( tmp.c_str( ), path.c_str( ) );
    }

    // Simulated buffers: a trigger pulse at the trigger position, PMT pulses
    // before it (a correlated one most of the time, with a spread, and random
    // ones), NIM levels, noise, and the 25 MHz bandwidth of the input.
    class Simulator {
        public:
            Simulator( const Options &o ) : opt( o ), rng( 12345 ) {}

            void Fill( vector<double> &pmt, vector<double> &trig )
            {
                const int    n   = opt.buffer;
                const double dt  = 1e9 / kSampleRate;
                const double lvl = 0.8;
                pmt.assign( n, 0 );
                trig.assign( n, 0 );

                uniform_real_distribution<double> uni( 0, 1 );
                normal_distribution<double>       noise( 0, 0.004 ), jitter( 0, 30 );

                double t_trig = ( opt.pre + uni( rng ) ) * dt;
                AddPulse( trig, t_trig, 60, lvl, dt, opt.trigger.falling );

                if ( uni( rng ) < 0.6 )
                    AddPulse( pmt, t_trig - 1200 + jitter( rng ), 50, lvl, dt, opt.pmt.falling );
                int randoms = (int)( uni( rng ) * 3 );
                for ( int k = 0; k < randoms; k++ )
                    AddPulse( pmt, uni( rng ) * ( n - 40 ) * dt, 50, lvl, dt, opt.pmt.falling );

                Smooth( pmt );
                Smooth( trig );
                for ( int i = 0; i < n; i++ ) {
                    pmt[i] += noise( rng );
                    trig[i] += noise( rng );
                }
            }

        private:
            void AddPulse( vector<double> &v, double t_ns, double width_ns, double level, double dt, bool falling )
            {
                for ( size_t i = 0; i < v.size( ); i++ ) {
                    double t = i * dt;
                    if ( t >= t_ns && t < t_ns + width_ns )
                        v[i] += falling ? -level : level;
                }
            }

            void Smooth( vector<double> &v )
            {
                const double tau = 6.4;  // ns, 25 MHz
                const double a   = 1e9 / kSampleRate / ( tau + 1e9 / kSampleRate );
                for ( size_t i = 1; i < v.size( ); i++ )
                    v[i] = v[i - 1] + a * ( v[i] - v[i - 1] );
            }

            Options opt;
            mt19937 rng;
    };

    // One ADALM2000 armed on the DAQ trigger channel.
    class Adalm {
        public:
            Adalm( const Options &o ) : opt( o ), m2k( nullptr ), ain( nullptr ) {}

            ~Adalm( )
            {
                try {
                    if ( ain )
                        ain->stopAcquisition( );
                    if ( m2k )
                        DisconnectAdalm( m2k );
                } catch ( ... ) {
                }
            }

            bool Open( )
            {
                m2k = ConnectToAdalmWithSerial( opt.serial );
                if ( !m2k )
                    return false;
                m2k->setTimeout( kReadTimeoutMs );

                ain = m2k->getAnalogIn( );
                ain->enableChannel( 0, true );
                ain->enableChannel( 1, true );
                ain->setSampleRate( kSampleRate );
                M2K_RANGE range = opt.high_range ? PLUS_MINUS_25V : PLUS_MINUS_2_5V;
                ain->setRange( ANALOG_IN_CHANNEL_1, range );
                ain->setRange( ANALOG_IN_CHANNEL_2, range );

                M2kHardwareTrigger *trig = ain->getTrigger( );
                int                 t    = opt.trigger.index;
                trig->setAnalogMode( opt.pmt.index, ALWAYS );
                trig->setAnalogMode( t, ANALOG );
                trig->setAnalogCondition( t, opt.trigger.falling ? FALLING_EDGE_ANALOG : RISING_EDGE_ANALOG );
                trig->setAnalogLevel( t, opt.trigger.threshold );
                trig->setAnalogSource( t == 0 ? CHANNEL_1 : CHANNEL_2 );
                trig->setAnalogDelay( -opt.pre );

                ain->startAcquisition( opt.buffer );
                return true;
            }

            // false when no trigger came within the read timeout
            bool Read( vector<double> &pmt, vector<double> &trig )
            {
                try {
                    vector<vector<double>> data = ain->getSamples( opt.buffer );
                    if ( data.size( ) < 2 )
                        return false;
                    pmt  = data[opt.pmt.index];
                    trig = data[opt.trigger.index];
                    return true;
                } catch ( const exception & ) {
                    return false;
                }
            }

        private:
            Options      opt;
            M2k         *m2k;
            M2kAnalogIn *ain;
    };

    struct Record {
            int                seq = 0;
            double             t_epoch = 0;
            float              trig_ns = 0;
            int                n_pmt   = 0;
            vector<float>      pmt_dt, pmt_amp, pmt_width;
            int                flags = 0;
            vector<float>      wave_pmt, wave_trig;
    };

    bool Saturated( const vector<double> &v, double limit )
    {
        for ( double x : v )
            if ( fabs( x ) >= limit )
                return true;
        return false;
    }

    // Times of the PMT pulses relative to the DAQ trigger edge of one buffer.
    void Analyze( const Options &o, const vector<double> &pmt, const vector<double> &trig, Record &r )
    {
        const double dt = 1e9 / kSampleRate;
        r.pmt_dt.clear( );
        r.pmt_amp.clear( );
        r.pmt_width.clear( );
        r.flags = 0;

        auto trig_pulses = SciPulse::Find( trig, o.trigger.threshold, o.trigger.falling, dt );
        int  k           = SciPulse::Nearest( trig_pulses, o.pre * dt, kTriggerWindow );
        if ( k < 0 ) {
            r.flags |= kNoTriggerEdge;
            r.trig_ns = 0;
            r.n_pmt   = 0;
            return;
        }
        r.trig_ns = (float)trig_pulses[k].cross_ns;

        for ( const auto &p : SciPulse::Find( pmt, o.pmt.threshold, o.pmt.falling, dt ) ) {
            r.pmt_dt.push_back( (float)( p.cross_ns - trig_pulses[k].cross_ns ) );
            r.pmt_amp.push_back( (float)p.amp );
            r.pmt_width.push_back( (float)p.width_ns );
        }
        r.n_pmt = (int)r.pmt_dt.size( );

        double limit = ( o.high_range ? 25. : 2.5 ) * kSaturation;
        if ( Saturated( pmt, limit ) || Saturated( trig, limit ) )
            r.flags |= kSaturated;
    }

    string MetaText( const Options &o, double start )
    {
        ostringstream s;
        s << fixed << setprecision( 3 );
        s << "serial=" << ( o.simulate ? "simulation" : o.serial ) << ";pmt_channel=" << o.pmt.index + 1 << ";pmt_threshold_V=" << o.pmt.threshold << ";pmt_edge=" << ( o.pmt.falling ? "falling" : "rising" )
          << ";trigger_channel=" << o.trigger.index + 1 << ";trigger_threshold_V=" << o.trigger.threshold << ";trigger_edge=" << ( o.trigger.falling ? "falling" : "rising" )
          << ";range=" << ( o.high_range ? "high" : "low" ) << ";buffer_samples=" << o.buffer << ";pre_trigger_samples=" << o.pre << ";sample_rate_Hz=" << setprecision( 0 ) << kSampleRate << setprecision( 3 ) << ";start_epoch=" << start;
        return s.str( );
    }

    void WriteInfo( const string &path, const Options &o, double start, long triggers, long pulses, const char *reason )
    {
        ofstream f( path.c_str( ) );
        f << fixed << setprecision( 3 );
        f << "start " << start << endl;
        f << "end " << Now( ) << endl;
        f << "triggers " << triggers << endl;
        f << "pmt_pulses " << pulses << endl;
        f << "reason " << reason << endl;
        f << MetaText( o, start ) << endl;
    }
}  // namespace

int main( int argc, char *argv[] )
{
    Options o;
    if ( !ParseOptions( argc, argv, o ) ) {
        Usage( );
        return 1;
    }

    signal( SIGTERM, OnSignal );
    signal( SIGINT, OnSignal );

    Adalm     adalm( o );
    Simulator sim( o );
    if ( !o.simulate && !adalm.Open( ) ) {
        cerr << " ERROR: cannot open the ADALM " << o.serial << endl;
        return 2;
    }

    TFile file( o.output.c_str( ), "RECREATE" );
    if ( file.IsZombie( ) ) {
        cerr << " ERROR: cannot create " << o.output << endl;
        return 3;
    }
    double start = Now( );
    TNamed meta( "meta", MetaText( o, start ).c_str( ) );
    meta.Write( );

    Record r;
    TTree  tree( "trigger", "one entry per trigger of the DAQ" );
    tree.Branch( "seq", &r.seq, "seq/I" );
    tree.Branch( "t_epoch", &r.t_epoch, "t_epoch/D" );
    tree.Branch( "trig_ns", &r.trig_ns, "trig_ns/F" );
    tree.Branch( "n_pmt", &r.n_pmt, "n_pmt/I" );
    tree.Branch( "pmt_dt", &r.pmt_dt );
    tree.Branch( "pmt_amp", &r.pmt_amp );
    tree.Branch( "pmt_width", &r.pmt_width );
    tree.Branch( "flags", &r.flags, "flags/I" );
    if ( o.waveform ) {
        tree.Branch( "wave_pmt", &r.wave_pmt );
        tree.Branch( "wave_trig", &r.wave_trig );
    }

    string status = WithSuffix( o.output, ".status" );
    WriteStatus( status, 0, 0 );
    cout << "READY" << endl;

    long   triggers = 0, pulses = 0;
    double last_status = 0;
    while ( !g_stop ) {
        vector<double> pmt, trig;
        if ( o.simulate ) {
            for ( double waited = 0; waited < 1. / o.sim_rate && !g_stop; waited += 0.05 )
                this_thread::sleep_for( chrono::duration<double>( min( 0.05, 1. / o.sim_rate ) ) );
            if ( g_stop )
                break;
            sim.Fill( pmt, trig );
        } else if ( !adalm.Read( pmt, trig ) ) {
            if ( Now( ) - last_status > 1 ) {
                WriteStatus( status, triggers, r.t_epoch );
                last_status = Now( );
            }
            continue;
        }

        r.seq     = (int)triggers;
        r.t_epoch = Now( );
        Analyze( o, pmt, trig, r );
        if ( o.waveform ) {
            r.wave_pmt.assign( pmt.begin( ), pmt.end( ) );
            r.wave_trig.assign( trig.begin( ), trig.end( ) );
        }
        tree.Fill( );
        triggers++;
        pulses += r.n_pmt;

        if ( triggers % kSaveEvery == 0 )
            tree.AutoSave( "SaveSelf" );
        if ( Now( ) - last_status > 1 ) {
            WriteStatus( status, triggers, r.t_epoch );
            last_status = Now( );
        }
    }

    file.cd( );
    tree.Write( );
    file.Close( );
    WriteStatus( status, triggers, r.t_epoch );
    WriteInfo( WithSuffix( o.output, ".info" ), o, start, triggers, pulses, "stopped" );
    return 0;
}
