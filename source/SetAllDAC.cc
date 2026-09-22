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
const double interval    = 0.1;  // seconds

void sleep_ms( double seconds )
{
    this_thread::sleep_for( chrono::duration<double>( seconds ) );
}

int main( int argc, char *argv[] )
{
    if ( argc != 5 && argc != 6 ) {
        cerr << " USAGE> SetAllDAC [IP address] [Vth value] [DAC data file] [bias value] [<calin channel>] " << endl;
        exit( 1 );
    }

    string IPaddr = argv[1];

    int vth = atoi( argv[2] );
    vth     = vth & 0x3fff;

    string filename = argv[3];

    int bias = atoi( argv[4] );
    bias     = bias & 0x3fff;

    int calin_channel = -1;
    if ( argc == 6 ) {
        calin_channel = atoi( argv[5] );
    }

    RBCP SlowCtrl;
    SlowCtrl.Open( IPaddr );

    // DAC channels (0x00-0x7f), Vth (0x80-0x81) and bias (0x82-0x83) are
    // contiguous shadow registers with no side effects on write, so they
    // are staged in one buffer and sent as a single RBCP transaction. Only
    // the apply strobes below (0xf0) actually take effect, and the
    // firmware requires exactly one of them at a time (RBCP_REG.vhd),
    // so those stay as three separate writes.
    char cmd[256];

    // =====================================================
    // Stage DAC values
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

        if ( ch == calin_channel ) {
            cmd[ch] = SlowCtrl.convDAC( dac, 1, 0 );
            cout << "ch: " << ch << " calin opened " << endl;
        } else {
            cmd[ch] = SlowCtrl.convDAC( dac, 0, 0 );
        }
    }

    // =====================================================
    // Stage Vth and bias
    // =====================================================

    cmd[channel_num + 0] = ( vth >> 8 ) & 0x3f;
    cmd[channel_num + 1] = vth & 0xff;
    cmd[channel_num + 2] = ( bias >> 8 ) & 0x3f;
    cmd[channel_num + 3] = bias & 0xff;

    cout << "Set DAC values, Vth : " << vth << ", bias : " << bias << endl;

    SlowCtrl.WriteRBCP( 0x00, cmd, channel_num + 4 );

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