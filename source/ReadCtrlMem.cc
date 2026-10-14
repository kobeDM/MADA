#include "../include/RBCP.h"
#include <cstdio>
#include <cstdlib>
#include <iomanip>
#include <iostream>

using namespace std;

int main( int argc, char *argv[] )
{
    if ( argc != 2 && argc != 4 ) {
        cerr << " USAGE> ReadCtrlMem [IP address] [<address> <length>] " << endl;
        exit( 1 );
    }
    string IPaddr = argv[1];

    RBCP SlowCtrl;
    SlowCtrl.Open( IPaddr );
    if ( argc == 4 ) {
        SlowCtrl.ReadRBCP( stoi( argv[2], nullptr, 0 ), stoi( argv[3], nullptr, 0 ) );
    } else {
        SlowCtrl.ReadRBCP( );
    }
}
