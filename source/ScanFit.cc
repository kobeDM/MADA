#include "../include/ScanEvent.h"
#include <TCanvas.h>
#include <TF1.h>
#include <TFile.h>
#include <TGraphErrors.h>
#include <TH1F.h>
#include <TH2F.h>
#include <TLine.h>
#include <TMath.h>
#include <TStyle.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

namespace
{
    const int    kMinPoints      = 6;     // fewest usable scan points for a fit
    const long   kMinEvents      = 20;    // fewest events for a usable scan point
    const double kRateFloor      = 0.02;  // lower bound of the error of a point
    const double kDeadMax        = 0.02;  // never above this rate: no hit
    const double kStuckMin       = 0.98;  // never below this rate: always hit
    const double kMinTransition  = 0.3;   // fewest rate change between the two ends

    struct Point {
            double value;
            string file;
    };

    struct Result {
            string cls    = "insufficient";
            double center = 0;   // x where the fitted rate is halfway between the plateaus
            double aligned = 0;  // x where the rate has risen to the level fraction of the transition from the no-hit side
            double sigma  = 0;  // erf width / sqrt(2)
            double lo     = 0;  // plateau rate at the start of the scan
            double hi     = 0;  // plateau rate at the end of the scan
            double chi2   = 0;
            int    npoints = 0;
    };

    string Trim( const string &s )
    {
        size_t b = s.find_first_not_of( " \t\r\n" );
        size_t e = s.find_last_not_of( " \t\r\n" );
        return b == string::npos ? "" : s.substr( b, e - b + 1 );
    }

    // key: value lines of scan_config.out
    map<string, string> ReadConfig( const string &name )
    {
        map<string, string> cfg;
        ifstream            f( name.c_str( ) );
        string              line;
        while ( getline( f, line ) ) {
            size_t c = line.find( ':' );
            if ( c == string::npos )
                continue;
            cfg[Trim( line.substr( 0, c ) )] = Trim( line.substr( c + 1 ) );
        }
        return cfg;
    }

    // scan_points.csv written by ScanAcquire: value,file,events,bytes,seconds,status
    bool ReadPoints( const string &dir, vector<Point> &points )
    {
        ifstream f( ( dir + "/scan_points.csv" ).c_str( ) );
        if ( !f )
            return false;
        string line;
        getline( f, line );
        while ( getline( f, line ) ) {
            stringstream ss( line );
            string       value, file;
            getline( ss, value, ',' );
            getline( ss, file, ',' );
            if ( value.empty( ) || file.empty( ) )
                continue;
            points.push_back( { atof( value.c_str( ) ), file } );
        }
        return true;
    }

    // Data of the old ScanVth (Vth_XXXX.scn) and DACSurvey (DAC_NN_XXXX.srv).
    bool ReadLegacyPoints( const string &dir, const string &mode, vector<Point> &points )
    {
        char name[128];
        if ( mode == "vth" ) {
            map<string, string> cfg = ReadConfig( dir + "/scan_config.out" );
            if ( !cfg.count( "Vth(lower)" ) )
                return false;
            int lo = atoi( cfg["Vth(lower)"].c_str( ) ), hi = atoi( cfg["Vth(upper)"].c_str( ) ), step = atoi( cfg["Vth(delta)"].c_str( ) );
            for ( int v = lo; step > 0 && v <= hi; v += step ) {
                snprintf( name, sizeof( name ), "Vth_%04x.scn", v );
                points.push_back( { (double)v, name } );
            }
            return true;
        }

        map<string, string> cfg = ReadConfig( dir + "/DACsurvey_config.out" );
        if ( !cfg.count( "Vth" ) )
            return false;
        int vth = atoi( cfg["Vth"].c_str( ) );
        for ( int d = 0; d < 64; d++ ) {
            snprintf( name, sizeof( name ), "DAC_%02d_%04x.srv", d, vth );
            points.push_back( { (double)d, name } );
        }
        return true;
    }

    // Position where the rate, coming from the no-hit end of the scan, first
    // reaches the level fraction of the transition. The tails of the noise
    // distribution are heavier than an error function, so this is read from
    // the data (linear interpolation) instead of the fit. A point counts only
    // when the next one is above the level too. Returns NaN when not found.
    double LevelCrossing( const vector<double> &x, const vector<double> &rate, double start, double end, double level )
    {
        const double nan = std::numeric_limits<double>::quiet_NaN( );
        int          n   = (int)x.size( );
        double       low = std::min( start, end ), high = std::max( start, end );
        double       lev = low + level * ( high - low );
        bool         from_end = end < start;  // the lower rate is at the end of the scan
        int          step     = from_end ? -1 : 1;
        int          i0       = from_end ? n - 1 : 0;

        for ( int k = 1; k < n; k++ ) {
            int i = i0 + step * k, prev = i - step, next = i + step;
            if ( rate[i] < lev || ( next >= 0 && next < n && rate[next] < lev ) )
                continue;
            if ( rate[i] == rate[prev] )
                return x[i];
            return x[prev] + ( lev - rate[prev] ) / ( rate[i] - rate[prev] ) * ( x[i] - x[prev] );
        }
        return nan;
    }

    // Mean of the first or the last three points.
    double Plateau( const vector<double> &v, bool first )
    {
        int    k = std::min( 3, (int)v.size( ) );
        double s = 0;
        for ( int i = 0; i < k; i++ )
            s += ( first ? v[i] : v[v.size( ) - 1 - i] ) / k;
        return s;
    }

    // Rate is a sum of two plateaus joined by an error function:
    // [0] * erf((x - [1]) / [2]) + [3]
    // Alignment on the events with a hit needs no fit: the channel is classified by
    // its occupancy over the scan and the level is read from the data.
    Result FitOccupancy( const vector<double> &x, const vector<double> &occupancy, double level )
    {
        Result r;
        r.npoints = (int)x.size( );
        if ( r.npoints < kMinPoints )
            return r;

        double top = *max_element( occupancy.begin( ), occupancy.end( ) );
        double bot = *min_element( occupancy.begin( ), occupancy.end( ) );
        if ( top < kDeadMax ) {
            r.cls = "dead";
            return r;
        }
        if ( bot > kStuckMin ) {
            r.cls = "stuck";
            return r;
        }

        r.lo = Plateau( occupancy, true );
        r.hi = Plateau( occupancy, false );
        if ( fabs( r.hi - r.lo ) < 0.5 ) {
            r.cls = "no_transition";
            return r;
        }

        r.aligned = LevelCrossing( x, occupancy, r.lo, r.hi, level );
        r.center  = r.aligned;
        r.cls     = r.aligned == r.aligned ? "ok" : "no_level";
        return r;
    }

    Result FitChannel( const vector<double> &x, const vector<double> &rate, const vector<double> &occupancy, const vector<double> &err, double step, double level, bool use_occupancy )
    {
        if ( use_occupancy )
            return FitOccupancy( x, occupancy, level );

        Result r;
        r.npoints = (int)x.size( );
        if ( r.npoints < kMinPoints )
            return r;

        double top = *max_element( rate.begin( ), rate.end( ) );
        double bot = *min_element( rate.begin( ), rate.end( ) );
        if ( top < kDeadMax ) {
            r.cls = "dead";
            return r;
        }
        if ( bot > kStuckMin ) {
            r.cls = "stuck";
            return r;
        }

        int    k  = std::min( 3, r.npoints / 2 );
        double lo = 0, hi = 0;
        for ( int i = 0; i < k; i++ ) {
            lo += rate[i] / k;
            hi += rate[r.npoints - 1 - i] / k;
        }
        r.lo = lo;
        r.hi = hi;
        if ( fabs( hi - lo ) < kMinTransition ) {
            r.cls = "no_transition";
            return r;
        }

        double mid = 0.5 * ( lo + hi ), c0 = 0.5 * ( x.front( ) + x.back( ) );
        for ( int i = 1; i < r.npoints; i++ ) {
            if ( ( rate[i - 1] - mid ) * ( rate[i] - mid ) <= 0 && rate[i] != rate[i - 1] ) {
                c0 = x[i - 1] + ( mid - rate[i - 1] ) / ( rate[i] - rate[i - 1] ) * ( x[i] - x[i - 1] );
                break;
            }
        }

        double  span = x.back( ) - x.front( );
        TGraphErrors g( r.npoints );
        for ( int i = 0; i < r.npoints; i++ ) {
            g.SetPoint( i, x[i], rate[i] );
            g.SetPointError( i, 0, err[i] );
        }
        TF1 f( "erf_fit", "[0] * TMath::Erf((x-[1])/[2]) + [3]", x.front( ), x.back( ) );
        f.SetParameters( 0.5 * ( hi - lo ), c0, std::max( span / 20., step ), mid );
        f.SetParLimits( 1, x.front( ), x.back( ) );
        f.SetParLimits( 2, step * 0.2, span );
        int status = g.Fit( &f, "QN0" );

        double w = f.GetParameter( 2 );
        bool   at_limit = w <= step * 0.2 * 1.001 || w >= span * 0.999;
        if ( status != 0 || at_limit || fabs( f.GetParameter( 0 ) ) < 0.5 * kMinTransition ) {
            r.cls = "fit_failed";
            return r;
        }
        r.cls    = "ok";
        r.center = f.GetParameter( 1 );
        r.aligned = level < 0.5 ? LevelCrossing( x, rate, r.lo, r.hi, level ) : r.center;
        if ( r.aligned != r.aligned ) {
            r.cls = "no_level";
            return r;
        }
        r.sigma  = w / sqrt( 2. );
        r.chi2   = f.GetNDF( ) > 0 ? f.GetChisquare( ) / f.GetNDF( ) : 0;
        return r;
    }
}  // namespace

int main( int argc, char *argv[] )
{
    if ( argc < 3 || argc > 6 ) {
        cerr << " USAGE> ScanFit [scan dir.] [vth|dac] [<target value> [<level> [rate|occupancy]]]" << endl;
        cerr << "   level (0 to 0.5, default 0.5): the position reported as 'aligned' is where the rate, coming from" << endl;
        cerr << "   the no-hit side, has risen to this fraction of the whole transition (read from the data by" << endl;
        cerr << "   interpolation). 0.5 is the fitted center, a small level is a point where the noise rate is low." << endl;
        cerr << "   The level counts the clocks with a hit (rate, default) or the events with a hit (occupancy)." << endl;
        cerr << "   The target value (the working Vth) is drawn as a red line in the scan plot." << endl;
        cerr << "   Fits the hit rate of every channel against the scanned value (Vth or DAC)" << endl;
        cerr << "   and writes fit_result.csv, fit_result.root, Vthcheck.png (or DACcheck.png) and fit_summary.png into the directory." << endl;
        return 1;
    }
    string dir  = argv[1];
    string mode = argv[2];
    double target = argc >= 4 ? atof( argv[3] ) : -1;
    double level  = argc >= 5 ? atof( argv[4] ) : 0.5;
    string metric = argc == 6 ? argv[5] : "rate";
    if ( metric != "rate" && metric != "occupancy" ) {
        cerr << " ERROR: the metric must be rate or occupancy" << endl;
        return 1;
    }
    if ( level <= 0 || level > 0.5 ) {
        cerr << " ERROR: level must be above 0 and at most 0.5" << endl;
        return 1;
    }
    if ( mode != "vth" && mode != "dac" ) {
        cerr << " ERROR: mode must be vth or dac" << endl;
        return 1;
    }

    vector<Point> points;
    if ( !ReadPoints( dir, points ) && !ReadLegacyPoints( dir, mode, points ) ) {
        cerr << " ERROR: no scan_points.csv or legacy scan configuration in " << dir << endl;
        return 1;
    }
    if ( points.empty( ) ) {
        cerr << " ERROR: no scan points" << endl;
        return 1;
    }

    double step = 1;
    if ( points.size( ) > 1 )
        step = fabs( points[1].value - points[0].value );

    vector<double>                  xs;
    vector<ScanEvent::Stats>        stats;
    vector<string>                  skipped;
    for ( const Point &p : points ) {
        vector<char> buf;
        if ( !ScanEvent::ReadFile( dir + "/" + p.file, buf ) ) {
            skipped.push_back( p.file + " (missing)" );
            continue;
        }
        ScanEvent::Stats st = ScanEvent::Parse( buf );
        if ( st.events < kMinEvents ) {
            skipped.push_back( p.file + " (" + to_string( st.events ) + " events)" );
            continue;
        }
        xs.push_back( p.value );
        stats.push_back( st );
    }
    cout << " Points: " << xs.size( ) << " used, " << skipped.size( ) << " skipped" << endl;
    for ( const string &s : skipped )
        cout << "   skipped " << s << endl;
    if ( xs.empty( ) ) {
        cerr << " ERROR: no usable scan point" << endl;
        return 1;
    }

    const int nch = ScanEvent::kChannels;
    vector<double> edges( xs.size( ) + 1 );
    for ( size_t i = 0; i <= xs.size( ); i++ ) {
        double below = i > 0 ? xs[i - 1] : xs[0] - step;
        double above = i < xs.size( ) ? xs[i] : xs.back( ) + step;
        edges[i]     = 0.5 * ( below + above );
    }
    string ip = ReadConfig( dir + "/scan_config.out" )["IP"];
    TH2F   image( "rate_image", ( mode == "vth" ? "Vth scan" : "DAC scan" ), nch, -0.5, nch - 0.5, xs.size( ), edges.data( ) );
    vector<Result> results( nch );
    TFile          root( ( dir + "/fit_result.root" ).c_str( ), "RECREATE" );

    for ( int ch = 0; ch < nch; ch++ ) {
        vector<double> rate, occupancy, err;
        for ( size_t i = 0; i < xs.size( ); i++ ) {
            double r = stats[i].Rate( ch );
            rate.push_back( r );
            occupancy.push_back( stats[i].Occupancy( ch ) );
            err.push_back( std::max( kRateFloor, sqrt( r * ( 1 - r ) / (double)stats[i].events ) ) );
            image.SetBinContent( ch + 1, i + 1, r );
        }
        results[ch] = FitChannel( xs, rate, occupancy, err, step, level, metric == "occupancy" );

        TGraphErrors *g = new TGraphErrors( xs.size( ) );
        g->SetName( Form( "rate_ch%03d", ch ) );
        g->SetTitle( Form( "Ch %03d (%s);%s;hit rate", ch, results[ch].cls.c_str( ), mode == "vth" ? "Vth" : "DAC" ) );
        for ( size_t i = 0; i < xs.size( ); i++ ) {
            g->SetPoint( i, xs[i], rate[i] );
            g->SetPointError( i, 0, err[i] );
        }
        g->Write( );
    }
    image.Write( );

    ofstream csv( ( dir + "/fit_result.csv" ).c_str( ) );
    csv << "ch,class,center,aligned,sigma,rate_start,rate_end,chi2_ndf,points" << endl;
    map<string, int> count;
    TH1F             centers( "centers", Form( "%s at %s level %g;channel", mode == "vth" ? "Fitted Vth" : "Fitted DAC", metric.c_str( ), level ), nch, -0.5, nch - 0.5 );
    vector<double>   good;
    for ( int ch = 0; ch < nch; ch++ ) {
        const Result &r = results[ch];
        count[r.cls]++;
        csv << ch << ',' << r.cls << ',' << r.center << ',' << r.aligned << ',' << r.sigma << ',' << r.lo << ',' << r.hi << ',' << r.chi2 << ',' << r.npoints << endl;
        if ( r.cls == "ok" ) {
            centers.SetBinContent( ch + 1, r.aligned );
            good.push_back( r.aligned );
        }
    }
    csv.close( );
    centers.Write( );
    root.Close( );

    gStyle->SetOptStat( 0 );
    const char *axis = mode == "vth" ? "Vth" : "DAC";
    image.SetTitle( Form( "%s scan ( %s, %s );channel;%s", axis, dir.c_str( ), ip.c_str( ), axis ) );
    image.GetZaxis( )->SetRangeUser( 0., 1.2 );

    TLine line( 0, target, nch, target );
    line.SetLineColor( 2 );
    line.SetLineWidth( 4 );

    TCanvas check( "check", "check", 800, 600 );
    image.Draw( "COLZ" );
    if ( target >= 0 )
        line.Draw( "same" );
    check.Print( ( dir + ( mode == "vth" ? "/Vthcheck.png" : "/DACcheck.png" ) ).c_str( ) );

    TCanvas c( "c", "c", 1000, 700 );
    c.Divide( 1, 2 );
    c.cd( 1 );
    image.Draw( "COLZ" );
    if ( target >= 0 )
        line.Draw( "same" );
    c.cd( 2 );
    centers.SetMarkerStyle( 20 );
    centers.SetMarkerSize( 0.6 );
    centers.SetLineWidth( 0 );
    if ( !good.empty( ) ) {
        double lo = *min_element( good.begin( ), good.end( ) ), hi = *max_element( good.begin( ), good.end( ) );
        double pad = std::max( 0.1 * ( hi - lo ), step );
        centers.GetYaxis( )->SetRangeUser( lo - pad, hi + pad );
    }
    centers.Draw( "P" );
    c.Print( ( dir + "/fit_summary.png" ).c_str( ) );

    cout << " Channels:";
    for ( auto &kv : count )
        cout << ' ' << kv.first << '=' << kv.second;
    cout << endl;
    if ( !good.empty( ) ) {
        sort( good.begin( ), good.end( ) );
        double mean = 0, var = 0;
        for ( double v : good )
            mean += v / good.size( );
        for ( double v : good )
            var += ( v - mean ) * ( v - mean ) / good.size( );
        printf( " Center (ok channels): median %.1f, mean %.1f, rms %.2f, min %.1f, max %.1f\n", good[good.size( ) / 2], mean, sqrt( var ), good.front( ), good.back( ) );
    }
    return 0;
}
