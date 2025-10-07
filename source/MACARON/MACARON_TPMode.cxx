#include <iostream>
#include "GPIOUtil.h"

int main( int argc, char* argv[] )
{
    if( argc != 2 ) {
        std::cerr << " Usage:" << std::endl;
        std::cerr << " $ MACARON_TPMode [1 (Enable) or 0 (Disable)]" << std::endl;
        exit(1);
    }

    std::cout << std::endl;
    unsigned int isTPMode = std::stoi( argv[1] );
    if( isTPMode != 0 ) {
        std::cout << "===== Testpulse mode: ON =====" << std::endl;
        isTPMode = 1;
    }
    else {
        std::cout << "===== Testpulse mode: OFF =====" << std::endl;
    }
    std::cout << std::endl;

    if( GPIOUtil::setFullValue( CHIP_ID_DAQ_TPMODE, WIDTH_DAQ_TPMODE, isTPMode ) == true ) {
        std::cout << "DAQ Control: succeeded in sending signal to GPIO!!!" << std::endl;
    }
    else {
        std::cerr << "ERROR: DAQ Control: failed to send signal to GPIO!!!" << std::endl;
    }
    
    return 0;
}
