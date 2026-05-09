#include "../include/AdalmUtil.h"

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

void DigitalLatchUp( M2kDigital *dout, const int channel[16] )
{
    const int    dmode = 1;  // 0 for opendrain, 1 for pushpull
    const int    ddir  = 1;  // 0 for input, 1 for output
    const double dfreq = 7.5e7;

    dout->setSampleRateOut( dfreq );

    for ( int i = 0; i < 16; i++ ) {
        dout->setOutputMode( i, DIO_MODE( dmode ) );
        dout->setDirection( i, DIO_DIRECTION( ddir ) );
    }

    dout->setCyclic( false );

    for ( int i = 0; i < 16; i++ ) {
        dout->setValueRaw( i, DIO_LEVEL( 1 ) );
    }
}

void DigitalLatchDown( M2kDigital *dout, const int channel[16] )
{
    const int    dmode = 1;  // 0 for opendrain, 1 for pushpull
    const int    ddir  = 1;  // 0 for input, 1 for output
    const double dfreq = 7.5e7;

    dout->setSampleRateOut( dfreq );

    for ( int i = 0; i < 16; i++ ) {
        dout->setOutputMode( i, DIO_MODE( dmode ) );
        dout->setDirection( i, DIO_DIRECTION( ddir ) );
    }

    dout->setCyclic( false );

    for ( int i = 0; i < 16; i++ ) {
        dout->setValueRaw( i, DIO_LEVEL( 0 ) );
    }
}

void DisconnectAdalm( M2k *m2k )
{
    if ( m2k ) {
        libm2k::context::contextClose( m2k );
    }
}
