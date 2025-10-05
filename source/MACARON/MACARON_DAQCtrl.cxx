#include <iostream>
#include "GPIOUtil.h"

int main( int argc, char* argv[] )
{
    if( argc != 2 ) {
        std::cerr << " Usage:" << std::endl;
        std::cerr << " $ MACARON_DAQCtrl [1 (Enable) or 0 (Disable)]" << std::endl;
        std::cerr << " Counter Reset will also be sent when 1 (Enable) is selected " << std::endl;
        exit(1);
    }

    std::cout << std::endl;
    unsigned int isEnable = std::stoi( argv[1] );
    if( isEnable != 0 ) {
        std::cout << "===== DAQ Control: Enable =====" << std::endl;
        isEnable = 1;
    }
    else {
        std::cout << "===== DAQ Control: Disable =====" << std::endl;
    }
    std::cout << std::endl;

    if( GPIOUtil::setFullValue( CHIP_ID_DAQ_ENABLE, WIDTH_DAQ_ENABLE, isEnable ) == true ) {
        std::cout << "DAQ Control: succeeded in sending signal to GPIO!!!" << std::endl;
    }
    else {
        std::cerr << "ERROR: DAQ Control: failed to send signal to GPIO!!!" << std::endl;
    }
    
    return 0;
}
