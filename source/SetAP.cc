#include "../include/RBCP.h"
#include <cstdio>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <unistd.h>

using namespace std;

int main( int argc, char *argv[] )
{
    if ( argc != 3 ) {
        cerr << " USAGE> SetAP [IP address] [0/1] " << endl;
        cerr << "   +-2.5V power supply flag 0...OFF, 1...ON " << endl;
        exit( 1 );
    }
    string IPaddr = argv[1];
    int    val    = atoi( argv[2] );
    val           = val & 0x1;

    RBCP SlowCtrl;
    SlowCtrl.Open( IPaddr );

    char cmd[256];

    if ( val == 1 ) {
        cmd[0] = 0x01;
    } else {
        cmd[0] = 0x00;
    }

    SlowCtrl.WriteRBCP( 0xf1, cmd, 1 );
    sleep( 1 );

    SlowCtrl.ReadRBCP( );
}
