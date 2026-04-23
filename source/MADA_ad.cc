#define _USE_MATH_DEFINES
#include <getopt.h>
#include <iomanip>
#include <iostream>
#include <libm2k/analog/m2kanalogin.hpp>
#include <libm2k/analog/m2kanalogout.hpp>
#include <libm2k/analog/m2kpowersupply.hpp>
#include <libm2k/contextbuilder.hpp>
#include <libm2k/digital/m2kdigital.hpp>  //for dio
#include <libm2k/m2k.hpp>
#include <math.h>
#include <sstream>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

#include "MADA_ad.h"

using namespace std;
using namespace libm2k;
using namespace libm2k::analog;
using namespace libm2k::digital;  // for dio
using namespace libm2k::context;

int ad_message( )
{
    cout << "ad message" << endl;
    return 0;
}

int ad_showIDs( M2k *ctx )
{
    cout << "\tURI:" << ctx->getUri( ) << endl;
    cout << "\tserial number:" << ctx->getSerialNumber( ) << endl;
    return 0;
}

int ad_d_setClock( M2kDigital *dio, int dfreq )
{
    dio->setSampleRateOut( dfreq );
    return 0;
}

int ad_d_init( M2kDigital *dio )
{
    int dmode = 1;  // 0 for opendrain, 1 for pushpull
    int ddir  = 1;  // 0 for input, 1 for output
    for ( int i = 0; i < 8; i++ ) {
        dio->setOutputMode( i, DIO_MODE( dmode ) );
        dio->setOutputMode( i + 8, DIO_MODE( dmode ) );
        dio->setDirection( i, DIO_DIRECTION( ddir ) );
        dio->setDirection( i + 8, DIO_DIRECTION( ddir ) );
    }
    dio->setCyclic( false );
    for ( int i = 0; i < 8; i++ ) {
        dio->setValueRaw( i, DIO_LEVEL( 0 ) );
        dio->setValueRaw( i + 8, DIO_LEVEL( 1 ) );
    }
    return 0;
}

int ad_d_enable( M2kDigital *dio )
{
    dio->enableAllOut( true );
    return 0;
}
int ad_d_latch_up( M2kDigital *dio )
{
    int ch = 6;
    for ( int i = 0; i < ch; i++ ) {
        dio->setValueRaw( i, DIO_LEVEL( 1 ) );
    }
    for ( int i = 0; i < ch; i++ ) {
        dio->setValueRaw( i + 8, DIO_LEVEL( 0 ) );
    }
    return 0;
}
int ad_d_latch_down( M2kDigital *dio )
{
    int ch = 6;
    for ( int i = 0; i < ch; i++ ) {
        dio->setValueRaw( i, DIO_LEVEL( 0 ) );
    }
    for ( int i = 0; i < ch; i++ ) {
        dio->setValueRaw( i + 8, DIO_LEVEL( 1 ) );
    }
    return 0;
}

int ad_d_cyclic( M2kDigital *dio, bool b )
{
    dio->setCyclic( b );
    return 0;
}

int ad_d_pulse( M2kDigital *dio, unsigned short data )
{
    int            dclocks = 30;
    unsigned short ddata[dclocks * 2];
    dio->setCyclic( false );
    for ( int i = 0; i < dclocks; i++ ) {
        ddata[i]           = data;
        ddata[i + dclocks] = ( data << 8 );
    }

    dio->enableAllOut( true );
    dio->push( ddata, dclocks * 2 );
    return 0;
}