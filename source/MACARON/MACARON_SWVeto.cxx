#include <iostream>
#include "GPIOUtil.h"

int main( int argc, char* argv[] )
{
    if( argc != 2 ) {
        std::cerr << " Usage:" << std::endl;
        std::cerr << " $ MACARON_SWVeto [1 (ON) or 0 (OFF)]" << std::endl;
        exit(1);
    }

    std::cout << std::endl;
    unsigned int isSWVeto = std::stoi( argv[1] );
    if( isSWVeto != 0 ) {
        std::cout << "===== Software veto: ON =====" << std::endl;
        isSWVeto = 1;
    }
    else {
        std::cout << "===== Software veto: OFF =====" << std::endl;
    }
    std::cout << std::endl;

    if( GPIOUtil::setFullValue( CHIP_ID_DAQ_SWVETO, WIDTH_DAQ_SWVETO, isSWVeto ) == true ) {
        std::cout << "DAQ Control: succeeded in sending signal to GPIO!!!" << std::endl;
    }
    else {
        std::cerr << "ERROR: DAQ Control: failed to send signal to GPIO!!!" << std::endl;
    }
    
    return 0;
}
