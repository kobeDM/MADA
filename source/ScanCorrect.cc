#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

namespace
{
    const int kChannels = 128;
    const int kDacMax   = 63;

    // A channel within this many DAC counts of the target is left alone: the
    // rounding to integer DAC values already limits the result to +-0.5, and
    // the statistical error of a fit would only make the value jump around.
    const double kDeadband = 0.6;

    struct Fit {
            string cls = "missing";
            double center = 0;
    };

    // fit_result.csv written by ScanFit
    bool ReadFit( const string &name, vector<Fit> &fits )
    {
        ifstream f( name.c_str( ) );
        if ( !f )
            return false;
        fits.assign( kChannels, Fit( ) );
        // the aligned position (fit at the chosen level); old files only have the center
        string line;
        getline( f, line );
        int column = -1, n = 0;
        {
            stringstream hs( line );
            string       name;
            while ( getline( hs, name, ',' ) ) {
                if ( name == "aligned" || ( name == "center" && column < 0 ) )
                    column = n;
                n++;
            }
        }
        if ( column < 0 )
            return false;
        while ( getline( f, line ) ) {
            stringstream ss( line );
            string       field, ch, cls, value;
            for ( int i = 0; getline( ss, field, ',' ); i++ ) {
                if ( i == 0 )
                    ch = field;
                if ( i == 1 )
                    cls = field;
                if ( i == column )
                    value = field;
            }
            int c = atoi( ch.c_str( ) );
            if ( c < 0 || c >= kChannels )
                continue;
            fits[c].cls    = cls;
            fits[c].center = atof( value.c_str( ) );
        }
        return true;
    }

    bool ReadDac( const string &name, vector<int> &dac )
    {
        ifstream f( name.c_str( ) );
        if ( !f )
            return false;
        dac.assign( kChannels, -1 );
        int ch, val;
        while ( f >> ch >> val )
            if ( ch >= 0 && ch < kChannels )
                dac[ch] = val;
        for ( int v : dac )
            if ( v < 0 || v > kDacMax )
                return false;
        return true;
    }

    bool WriteDac( const string &name, const vector<int> &dac )
    {
        ofstream f( name.c_str( ) );
        if ( !f )
            return false;
        for ( int ch = 0; ch < kChannels; ch++ )
            f << ch << '\t' << dac[ch] << endl;
        return true;
    }

    double Median( vector<double> v )
    {
        if ( v.empty( ) )
            return 0;
        sort( v.begin( ), v.end( ) );
        size_t n = v.size( );
        return n % 2 ? v[n / 2] : 0.5 * ( v[n / 2 - 1] + v[n / 2] );
    }

    double Rms( const vector<double> &v )
    {
        if ( v.empty( ) )
            return 0;
        double m = 0, s = 0;
        for ( double x : v )
            m += x / v.size( );
        for ( double x : v )
            s += ( x - m ) * ( x - m ) / v.size( );
        return sqrt( s );
    }

    int Clamp( double v )
    {
        return std::max( 0, std::min( kDacMax, (int)floor( v + 0.5 ) ) );
    }

    void Usage( )
    {
        cerr << " USAGE> ScanCorrect dac [DAC fit csv] [reference DAC file | none] [out DAC file]" << endl;
        cerr << "          DAC file from a DAC scan: the DAC where each channel crosses the scanned Vth." << endl;
        cerr << "          Channels that could not be fitted take their value from the reference file" << endl;
        cerr << "          (or the median of the fitted channels without one)." << endl;
        cerr << "        ScanCorrect slope [DAC fit csv at Vth0] [Vth0] [DAC fit csv at Vth1] [Vth1]" << endl;
        cerr << "          Measured Vth counts per DAC count (median over channels fitted in both scans)." << endl;
        cerr << "        ScanCorrect refine [Vth fit csv] [DAC file] [slope] [out DAC file] [target Vth | median]" << endl;
        cerr << "          Moves the DAC of every fitted channel so that its Vth center meets the target." << endl;
        cerr << " Results are printed as 'key: value' lines." << endl;
    }

    int RunDac( const string &fitname, const string &refname, const string &outname )
    {
        vector<Fit> fits;
        if ( !ReadFit( fitname, fits ) ) {
            cerr << " ERROR: cannot read " << fitname << endl;
            return 1;
        }
        vector<int> ref;
        if ( refname != "none" && !ReadDac( refname, ref ) ) {
            cerr << " ERROR: cannot read the reference DAC file " << refname << endl;
            return 1;
        }

        vector<double> okvals;
        for ( const Fit &f : fits )
            if ( f.cls == "ok" )
                okvals.push_back( f.center );
        if ( okvals.empty( ) ) {
            cerr << " ERROR: no channel could be fitted" << endl;
            return 1;
        }

        int         fallback = Clamp( Median( okvals ) );
        vector<int> dac( kChannels );
        int         nfit = 0, nclamp = 0;
        for ( int ch = 0; ch < kChannels; ch++ ) {
            if ( fits[ch].cls == "ok" ) {
                dac[ch] = Clamp( fits[ch].center );
                if ( fits[ch].center < -0.5 || fits[ch].center > kDacMax + 0.5 )
                    nclamp++;
                nfit++;
            } else {
                dac[ch] = ref.empty( ) ? fallback : ref[ch];
                cout << "unfitted_channel: " << ch << " " << fits[ch].cls << " -> " << dac[ch] << endl;
            }
        }
        if ( !WriteDac( outname, dac ) ) {
            cerr << " ERROR: cannot write " << outname << endl;
            return 1;
        }
        cout << "fitted: " << nfit << endl;
        cout << "unfitted: " << kChannels - nfit << endl;
        cout << "clamped: " << nclamp << endl;
        cout << "dac_median: " << Median( okvals ) << endl;
        cout << "dac_rms: " << Rms( okvals ) << endl;
        return 0;
    }

    int RunSlope( const string &name0, double vth0, const string &name1, double vth1 )
    {
        vector<Fit> f0, f1;
        if ( !ReadFit( name0, f0 ) || !ReadFit( name1, f1 ) ) {
            cerr << " ERROR: cannot read the fit results" << endl;
            return 1;
        }
        vector<double> k;
        for ( int ch = 0; ch < kChannels; ch++ ) {
            if ( f0[ch].cls != "ok" || f1[ch].cls != "ok" )
                continue;
            double d = f1[ch].center - f0[ch].center;
            if ( fabs( d ) < 0.5 )
                continue;
            k.push_back( ( vth1 - vth0 ) / d );
        }
        if ( k.size( ) < 8 ) {
            cerr << " ERROR: only " << k.size( ) << " channels fitted in both scans" << endl;
            return 1;
        }
        cout << "slope: " << Median( k ) << endl;
        cout << "slope_rms: " << Rms( k ) << endl;
        cout << "channels: " << k.size( ) << endl;
        return 0;
    }

    int RunRefine( const string &fitname, const string &dacname, double slope, const string &outname, const string &target_arg )
    {
        vector<Fit> fits;
        vector<int> dac;
        if ( !ReadFit( fitname, fits ) ) {
            cerr << " ERROR: cannot read " << fitname << endl;
            return 1;
        }
        if ( !ReadDac( dacname, dac ) ) {
            cerr << " ERROR: cannot read 128 DAC values from " << dacname << endl;
            return 1;
        }
        if ( slope == 0 ) {
            cerr << " ERROR: the slope must not be zero" << endl;
            return 1;
        }

        vector<double> centers;
        for ( const Fit &f : fits )
            if ( f.cls == "ok" )
                centers.push_back( f.center );
        if ( centers.empty( ) ) {
            cerr << " ERROR: no channel could be fitted" << endl;
            return 1;
        }
        double target = target_arg == "median" ? Median( centers ) : atof( target_arg.c_str( ) );

        vector<int>    out = dac;
        vector<double> before, after;
        int            changed = 0, clamped = 0;
        for ( int ch = 0; ch < kChannels; ch++ ) {
            if ( fits[ch].cls != "ok" )
                continue;
            double offset = ( fits[ch].center - target ) / slope;
            double want   = dac[ch] - offset;
            out[ch]       = fabs( offset ) > kDeadband ? Clamp( want ) : dac[ch];
            if ( fabs( offset ) > kDeadband && ( want < -0.5 || want > kDacMax + 0.5 ) )
                clamped++;
            if ( out[ch] != dac[ch] )
                changed++;
            before.push_back( ( fits[ch].center - target ) / slope );
            after.push_back( ( fits[ch].center - target ) / slope + ( out[ch] - dac[ch] ) );
        }
        if ( !WriteDac( outname, out ) ) {
            cerr << " ERROR: cannot write " << outname << endl;
            return 1;
        }
        cout << "target: " << target << endl;
        cout << "fitted: " << centers.size( ) << endl;
        cout << "changed: " << changed << endl;
        cout << "clamped: " << clamped << endl;
        cout << "offset_rms_dac_before: " << sqrt( inner_product( before.begin( ), before.end( ), before.begin( ), 0. ) / before.size( ) ) << endl;
        cout << "offset_rms_dac_after: " << sqrt( inner_product( after.begin( ), after.end( ), after.begin( ), 0. ) / after.size( ) ) << endl;
        return 0;
    }
}  // namespace

int main( int argc, char *argv[] )
{
    string cmd = argc > 1 ? argv[1] : "";
    if ( cmd == "dac" && argc == 5 )
        return RunDac( argv[2], argv[3], argv[4] );
    if ( cmd == "slope" && argc == 6 )
        return RunSlope( argv[2], atof( argv[3] ), argv[4], atof( argv[5] ) );
    if ( cmd == "refine" && argc == 7 )
        return RunRefine( argv[2], argv[3], atof( argv[4] ), argv[5], argv[6] );

    Usage( );
    return 1;
}
