#include <iostream>
#include "GPIOUtil.h"

int main( int argc, char* argv[] )
{
    if( argc != 1 ) {
        std::cerr << " Usage:" << std::endl;
        std::cerr << " $ MACARON_CntReset" << std::endl;

        exit(1);
    }

    std::cout << std::endl;
    std::cout << "===== DAQ Counter Reset =====" << std::endl;
    std::cout << std::endl;

    int retVal = -1;
    if( GPIOUtil::setFullValue( CHIP_ID_DAQ_COUNT_RESET, WIDTH_DAQ_COUNT_RESET, 0 ) == true ) {
        std::cout << "DAQ Counter Reset: reset start" << std::endl;
        if( GPIOUtil::setFullValue( CHIP_ID_DAQ_COUNT_RESET, WIDTH_DAQ_COUNT_RESET, 1 ) == true &&
            GPIOUtil::setFullValue( CHIP_ID_DAQ_COUNT_RESET, WIDTH_DAQ_COUNT_RESET, 0 ) == true ) {
            std::cout << "DAQ Counter Reset: Success!!!" << std::endl;
            retVal = 0;
        }
    }
    else {
        std::cerr << "ERROR: DAQ Counter Reset: failed to send reset signal" << std::endl;
        GPIOUtil::setFullValue( CHIP_ID_DAQ_COUNT_RESET, WIDTH_DAQ_COUNT_RESET, 0 );
    }
    
    return retVal;
}
