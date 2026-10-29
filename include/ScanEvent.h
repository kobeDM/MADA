#ifndef ScanEvent_h
#define ScanEvent_h 1

#include <arpa/inet.h>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

namespace ScanEvent
{
    const int      kChannels   = 128;
    const int      kClockDepth = 1024;  // encoding clock depth (rows per event at most)
    const uint32_t kHeader     = 0xeb901964;
    const uint32_t kFooter     = 0x75504943;  // "uPIC"

    // Per-channel hit statistics of one scan point.
    struct Stats {
            long   events = 0;  // complete events, including the ones without any hit row
            long   empty  = 0;  // events without hit data
            long   broken = 0;  // incomplete or malformed events (not counted in events)
            double rows[kChannels];
            double hitEvents[kChannels];  // events in which the channel was hit at least once

            Stats( )
            {
                std::memset( rows, 0, sizeof( rows ) );
                std::memset( hitEvents, 0, sizeof( hitEvents ) );
            }

            // Fraction of the clock depth in which the channel was hit, per event.
            double Rate( int ch ) const { return events > 0 ? rows[ch] / ( (double)events * kClockDepth ) : 0.; }

            // Fraction of the events in which the channel was hit at all.
            double Occupancy( int ch ) const { return events > 0 ? hitEvents[ch] / (double)events : 0.; }
    };

    inline uint32_t Word( const std::vector<char> &buf, size_t pos )
    {
        uint32_t w;
        std::memcpy( &w, &buf[pos], 4 );
        return ntohl( w );
    }

    // Parse a stream of events; an event is header, 3 counters, then either
    // the footer (no hit) or 1025 words of waveform data, hit rows (5 words:
    // row header + 128 bits) and the footer.
    inline Stats Parse( const std::vector<char> &buf )
    {
        Stats        st;
        const size_t n     = buf.size( );
        size_t       pos   = 0;
        const size_t kPre  = 16;                      // header + 3 counters
        const size_t kWave = 1025 * 4;                // words between the counters and the hit rows

        while ( pos + kPre + 4 <= n ) {
            if ( Word( buf, pos ) != kHeader ) {
                pos++;
                continue;
            }
            size_t p = pos + kPre;
            if ( Word( buf, p ) == kFooter ) {
                st.events++;
                st.empty++;
                pos = p + 4;
                continue;
            }

            p += kWave;
            double rows[kChannels] = { 0 };
            bool   ok              = false;
            while ( p + 4 <= n ) {
                if ( Word( buf, p ) == kFooter ) {
                    ok = true;
                    break;
                }
                if ( p + 20 > n )
                    break;
                for ( int i = 0; i < 4; i++ ) {
                    uint32_t w = Word( buf, p + 4 + 4 * i );
                    for ( int s = 0; s < 32; s++ )
                        if ( ( w >> s ) & 0x1 )
                            rows[32 * ( 3 - i ) + s] += 1;
                }
                p += 20;
            }

            if ( !ok ) {
                st.broken++;
                pos++;  // resynchronize on the next header
                continue;
            }
            st.events++;
            for ( int ch = 0; ch < kChannels; ch++ ) {
                st.rows[ch] += rows[ch];
                if ( rows[ch] > 0 )
                    st.hitEvents[ch] += 1;
            }
            pos = p + 4;
        }
        return st;
    }

    inline bool ReadFile( const std::string &name, std::vector<char> &buf )
    {
        std::ifstream f( name.c_str( ), std::ios::binary );
        if ( !f )
            return false;
        buf.assign( ( std::istreambuf_iterator<char>( f ) ), std::istreambuf_iterator<char>( ) );
        return true;
    }
}  // namespace ScanEvent

#endif
