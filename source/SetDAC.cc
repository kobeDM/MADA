#include "../include/RBCP.h"
#include <cstdio>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <unistd.h>

using namespace std;

int main( int argc, char *argv[] )
{
    if ( argc != 3 && argc != 4 ) {
        cerr << " USAGE> SetDAC [IP address] [DAC data file] [<channel>] " << endl;
        exit( 1 );
    }
    string IPaddr   = argv[1];
    string filename = argv[2];

    int channel = -1;
    if ( argc == 4 ) {
        channel = atoi( argv[3] );
    }

    RBCP SlowCtrl;
    SlowCtrl.Open( IPaddr );

    char     cmd[256];
    ifstream DAC_data( filename.c_str( ) );
    if ( !DAC_data ) {
        cerr << " ERROR: file not exist " << endl;
        exit( 1 );
    }
    for ( int i = 0; i < 128; i++ ) {
        int ch, dac;
        DAC_data >> ch >> dac;
        if ( channel == -1 || channel != ch ) {
            cmd[ch] = SlowCtrl.convDAC( dac, 0, 0 );
        } else {
            cmd[ch] = SlowCtrl.convDAC( dac, 1, 0 );
            std::cout << "ch: " << ch << " calin opened " << std::endl;
        }
    }
    SlowCtrl.WriteRBCP( 0, cmd, 128 );

    cmd[0] = 0x02;
    SlowCtrl.WriteRBCP( 0xf0, cmd, 1 );
    sleep( 1 );

    SlowCtrl.ReadRBCP( 0x00, 0x8f );
    SlowCtrl.ReadRBCP( 0xf0, 0x0f );
}
