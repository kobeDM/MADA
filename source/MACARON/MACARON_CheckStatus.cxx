#include <iostream>
#include <cstring>
#include "GPIOUtil.h"

void usage( )
{
    std::cerr << " Usage:" << std::endl;
    std::cerr << " $ MACARON_CheckStatus [-tp] [-sv]" << std::endl;
    std::cerr << "    DAQ_ENABLE status will be checked by default. check parameter can be selected by below option." << std::endl;
    std::cerr << "    NOTE: only one option is permitted." << std::endl;
    std::cerr << "    [-tp]: check testpulse mode" << std::endl;
    std::cerr << "    [-sv]: check software veto" << std::endl;
    return;
}


int main( int argc, char* argv[] )
{
    if( argc > 2 ) {
        usage( );
        exit(1);
    }
    std::cout << std::endl;

    bool is_tpmode = false;
    bool is_swveto = false;
    if( argc == 2 ) {
        std::string argStr = argv[1];
        if( argStr == "-tp" ) {
            is_tpmode = true;
            std::cout << " === Check testpulse mode === " << std::endl;
        }
        else if( argStr == "-sv" ) {
            is_swveto = true;
            std::cout << " === Check software veto === " << std::endl;
        }
        else {
            usage( );
            exit( 1 );
        }
    }
    else {
        std::cout << " === Check DAQ Enable mode === " << std::endl;
    }

    unsigned int chipID = CHIP_ID_DAQ_ENABLE;
    unsigned int width  = WIDTH_DAQ_ENABLE;
    if( is_tpmode == true ) {
        chipID = CHIP_ID_DAQ_TPMODE;
        width  = WIDTH_DAQ_TPMODE;
    }
    else if( is_swveto == true ) {
        chipID = CHIP_ID_DAQ_SWVETO;
        width  = WIDTH_DAQ_SWVETO;
    }

    unsigned int status = GPIOUtil::getFullValue( chipID, width );
    
    return static_cast< int >( status );
}
