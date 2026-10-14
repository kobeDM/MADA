#include "../include/AdalmUtil.h"

#include <algorithm>
#include <chrono>
#include <thread>

M2k *ConnectToAdalmWithSerial( const std::string &serialNumber )
{
    auto contexts = libm2k::context::getAllContexts( );

    M2k *selected = nullptr;

    for ( const auto &uri : contexts ) {
        M2k *m2k = libm2k::context::m2kOpen( uri.c_str( ) );

        if ( !m2k )
            continue;

        std::string serial = m2k->getSerialNumber( );

        std::cout << "Found: " << serial << " @ " << uri << std::endl;

        if ( serial == serialNumber ) {
            selected = m2k;
            break;
        }

        libm2k::context::contextClose( m2k );
    }

    if ( !selected ) {
        std::cerr << "Target device not found." << std::endl;
        return nullptr;
    }

    // calibrateADC/DAC are intentionally not called: with another ADALM latched
    // up, the calibration load resets the shared USB hub and every ADALM drops
    // off the bus for ~5 s. Only digital levels and a DC level are driven here.
    return selected;
}

void AnalogDcOut( M2kAnalogOut *aout, int channel, double voltage )
{
    const double        freq = 7.5e7;
    std::vector<double> pulse( 1024, voltage );
    aout->setSampleRate( channel, freq );
    aout->enableChannel( channel, true );
    aout->setCyclic( false );
    aout->push( channel, pulse );
    std::cout << "Analog DC output: channel " << channel << ", voltage " << voltage << " V" << std::endl;
}

// Writing the lines one by one with setValueRaw spreads the edges over about
// 1.2 ms per line, so lines that must change together (e.g. the four counter
// reset lines) are instead moved by a short buffer, which changes every line on
// the same sample. The buffer only drives the lines of this call (the TX of all
// other lines is disabled, so they keep their level), and after it ends a line
// falls back to its static value, which is therefore written during the buffer.
namespace {
const int    DIO_MODE_PUSHPULL = 1;     // 0 for opendrain, 1 for pushpull
const int    DIO_DIR_OUTPUT    = 1;     // 0 for input, 1 for output
const double BUFFER_RATE       = 1e6;   // Hz
const double STATIC_WINDOW     = 0.05;  // s, must exceed the per-line static writes (about 1.2 ms each)
const double PULSE_TAIL        = 0.05;  // s, extra wait for the buffer to drain

unsigned short ChannelMask( const int channel[16] )
{
    unsigned short mask = 0;
    for ( int i = 0; i < 16; i++ ) {
        if ( channel[i] )
            mask |= static_cast<unsigned short>( 1u << i );
    }
    return mask;
}

void SetLinesToOutput( M2kDigital *dout, const int channel[16] )
{
    for ( int i = 0; i < 16; i++ ) {
        if ( !channel[i] )
            continue;

        dout->setOutputMode( i, DIO_MODE( DIO_MODE_PUSHPULL ) );
        dout->setDirection( i, DIO_DIRECTION( DIO_DIR_OUTPUT ) );
    }
}

void EnableBufferOnly( M2kDigital *dout, const int channel[16] )
{
    dout->setCyclic( false );
    dout->setSampleRateOut( BUFFER_RATE );
    for ( int i = 0; i < 16; i++ )
        dout->enableChannel( i, channel[i] != 0 );
}

void DisableBuffer( M2kDigital *dout )
{
    for ( int i = 0; i < 16; i++ )
        dout->enableChannel( i, false );
}

void DigitalWrite( M2kDigital *dout, const int channel[16], int level )
{
    const unsigned short mask = ChannelMask( channel );

    SetLinesToOutput( dout, channel );
    EnableBufferOnly( dout, channel );

    std::vector<unsigned short> buffer( static_cast<size_t>( STATIC_WINDOW * BUFFER_RATE ), level ? mask : 0 );
    dout->push( buffer );

    for ( int i = 0; i < 16; i++ ) {
        if ( channel[i] )
            dout->setValueRaw( i, DIO_LEVEL( level ) );
    }

    std::this_thread::sleep_for( std::chrono::duration<double>( STATIC_WINDOW ) );
    DisableBuffer( dout );
}
}  // namespace

void DigitalLatchUp( M2kDigital *dout, const int channel[16] )
{
    DigitalWrite( dout, channel, 1 );
}

void DigitalLatchDown( M2kDigital *dout, const int channel[16] )
{
    DigitalWrite( dout, channel, 0 );
}

void DigitalPulse( M2kDigital *dout, const int channel[16], double width )
{
    const unsigned short mask = ChannelMask( channel );

    // The static value (LOW) is what the lines return to after the buffer.
    SetLinesToOutput( dout, channel );
    for ( int i = 0; i < 16; i++ ) {
        if ( channel[i] )
            dout->setValueRaw( i, DIO_LEVEL( 0 ) );
    }

    EnableBufferOnly( dout, channel );

    size_t high = static_cast<size_t>( width * BUFFER_RATE );
    high        = ( ( high + 3 ) / 4 ) * 4;
    std::vector<unsigned short> buffer( high + 64, 0 );
    std::fill( buffer.begin( ), buffer.begin( ) + high, mask );
    dout->push( buffer );

    std::this_thread::sleep_for( std::chrono::duration<double>( width + PULSE_TAIL ) );
    DisableBuffer( dout );
}

void OutputWaveformSquare( M2kAnalogOut *aout, int channel, double voltage, double frequency )
{
    const int           samples = 1024;
    std::vector<double> pulse( samples );

    for ( int i = 0; i < samples; i++ ) {
        pulse[i] = ( i < samples / 2 ) ? voltage * 0.5 : -voltage * 0.5;
    }

    aout->setSampleRate( channel, frequency * samples );
    aout->enableChannel( channel, true );
    aout->setCyclic( true );
    aout->push( channel, pulse );
    std::cout << "Analog square waveform output: channel " << channel << ", voltage " << voltage << " V, frequency " << frequency << " Hz" << std::endl;
}

// Data aquisition
// void ReadAnalogInput( M2kAnalogIn *ain, int channel, int samples )
// {
//     ain->setSampleRate( channel, 7.5e7 );
//     ain->enableChannel( channel, true );
//     std::vector<double> data = ain->pull( channel, samples );
//     std::cout << "Analog input read: channel " << channel << ", samples " << samples << std::endl;
//     for ( size_t i = 0; i < data.size( ); i++ ) {
//         std::cout << "Sample " << i << ": " << data[i] << " V" << std::endl;
//     }
// }

void DisconnectAdalm( M2k *m2k )
{
    if ( m2k ) {
        libm2k::context::contextClose( m2k );
    }
}
