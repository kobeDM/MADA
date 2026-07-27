#include "../include/RBCP.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <thread>
#include <unistd.h>

using namespace std;

const int    channel_num = 128;
const double interval    = 1.0;  // seconds

void sleep_ms( double seconds )
{
    this_thread::sleep_for( chrono::duration<double>( seconds ) );
}

int main( int argc, char *argv[] )
{
    if ( argc != 5 ) {
        cerr << " USAGE> SetDAC [IP address] [Vth value] [DAC data file] [bias value] " << endl;
        exit( 1 );
    }

    string IPaddr = argv[1];

    int vth = atoi( argv[2] );
    vth     = vth & 0x3fff;

    string filename = argv[3];

    int bias = atoi( argv[4] );
    bias     = bias & 0x3fff;

    RBCP SlowCtrl;
    SlowCtrl.Open( IPaddr );

    char cmd[256];

    // =====================================================
    // Set Vth
    // =====================================================

    cmd[0] = ( vth >> 8 ) & 0x3f;
    cmd[1] = vth & 0xff;

    cout << "Set Vth : " << vth << endl;

    SlowCtrl.WriteRBCP( 0x80, cmd, 2 );

    sleep_ms( interval );

    // =====================================================
    // Set DAC values
    // =====================================================

    ifstream DAC_data( filename.c_str( ) );

    if ( !DAC_data ) {
        cerr << " ERROR: file not exist " << endl;
        exit( 1 );
    }

    for ( int i = 0; i < channel_num; i++ ) {

        int ch;
        int dac;

        DAC_data >> ch >> dac;

        cmd[ch] = SlowCtrl.convDAC( dac, 0, 0 );
    }

    cout << "Set DAC values" << endl;

    SlowCtrl.WriteRBCP( 0x00, cmd, channel_num );

    sleep_ms( interval );

    // =====================================================
    // Set bias
    // =====================================================

    cmd[0] = ( bias >> 8 ) & 0x3f;
    cmd[1] = bias & 0xff;

    cout << "Set bias : " << bias << endl;

    SlowCtrl.WriteRBCP( 0x82, cmd, 2 );

    sleep_ms( interval );

    // =====================================================
    // Apply configuration
    // =====================================================

    cout << "Write Vth" << endl;

    cmd[0] = 0x01;
    SlowCtrl.WriteRBCP( 0xf0, cmd, 1 );

    sleep_ms( interval );

    cout << "Write DAC values" << endl;

    cmd[0] = 0x02;
    SlowCtrl.WriteRBCP( 0xf0, cmd, 1 );

    sleep_ms( interval );

    cout << "Write bias" << endl;

    cmd[0] = 0x04;
    SlowCtrl.WriteRBCP( 0xf0, cmd, 1 );

    sleep_ms( interval );

    // =====================================================
    // Readback
    // =====================================================

    SlowCtrl.ReadRBCP( 0x00, 0x8f );
    SlowCtrl.ReadRBCP( 0xf0, 0x0f );

    return 0;
}