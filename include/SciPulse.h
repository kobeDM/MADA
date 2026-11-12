#ifndef SciPulse_h
#define SciPulse_h 1

#include <cmath>
#include <vector>

// Pulse search in a sampled NIM-like waveform of the SCI mode.
namespace SciPulse
{
    const int kMergeGap = 2;  // samples above the threshold that still belong to one pulse

    struct Pulse {
            double cross_ns;  // time the signal crossed the threshold, from the first sample (interpolated)
            double amp;       // most extreme voltage of the pulse
            double width_ns;  // time below (above) the threshold; -1 when the pulse is cut by the end of the buffer
    };

    inline bool Beyond( double v, double threshold, bool falling )
    {
        return falling ? v < threshold : v > threshold;
    }

    // Pulses of the waveform. A pulse that is already beyond the threshold in
    // the first sample has no crossing time and is left out.
    inline std::vector<Pulse> Find( const std::vector<double> &v, double threshold, bool falling, double sample_ns )
    {
        std::vector<Pulse> pulses;
        const int          n = (int)v.size( );
        int                i = 1;
        while ( i < n ) {
            if ( !( Beyond( v[i], threshold, falling ) && !Beyond( v[i - 1], threshold, falling ) ) ) {
                i++;
                continue;
            }

            Pulse p;
            double dv   = v[i] - v[i - 1];
            p.cross_ns  = ( ( i - 1 ) + ( threshold - v[i - 1] ) / dv ) * sample_ns;
            p.amp       = v[i];
            p.width_ns  = -1;

            int end = i;  // last sample of the pulse
            for ( int j = i; j < n; j++ ) {
                if ( Beyond( v[j], threshold, falling ) ) {
                    end = j;
                    p.amp = falling ? std::min( p.amp, v[j] ) : std::max( p.amp, v[j] );
                } else if ( j - end > kMergeGap ) {
                    break;
                }
            }

            if ( end + 1 < n ) {
                double back = ( end + ( threshold - v[end] ) / ( v[end + 1] - v[end] ) ) * sample_ns;
                p.width_ns  = back - p.cross_ns;
            }
            pulses.push_back( p );
            i = end + 1;
        }
        return pulses;
    }

    // The pulse of the list whose crossing is closest to the expected time, or -1.
    inline int Nearest( const std::vector<Pulse> &pulses, double expected_ns, double tolerance_ns )
    {
        int    best = -1;
        double dist = tolerance_ns;
        for ( size_t k = 0; k < pulses.size( ); k++ ) {
            double d = std::fabs( pulses[k].cross_ns - expected_ns );
            if ( d <= dist ) {
                dist = d;
                best = (int)k;
            }
        }
        return best;
    }
}  // namespace SciPulse

#endif
