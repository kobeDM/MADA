#include <iostream>
#include <gpiod.h>
#include "GPIOUtil.h"


unsigned int GPIOUtil::getFullValue( const unsigned int& chipID,
                                     const unsigned int& width )
{
    unsigned int retVal = 0;
    std::string binaryStr = "";
    for( int bit = 0; bit < width; ++bit ) {
        
        // open GPIO chip
        std::string chipPath = GPIO_DEV_CHIP_PATH + std::to_string( chipID );

        struct gpiod_chip* pChip = gpiod_chip_open( chipPath.c_str( ) );
        if( pChip == nullptr ) {
            std::cerr << "ERROR: failed to open GPIO chip: " << chipID << "." << std::endl;
            break;
        }

        struct gpiod_line* pLine = gpiod_chip_get_line( pChip, bit );
        if( pLine == nullptr ) {
            std::cerr << "ERROR: failed to open GPIO chip line: " << bit << "." << std::endl;
            gpiod_chip_close( pChip );
            break;
        }

        if( gpiod_line_request_input( pLine, "" ) == -1 ) {
            std::cerr << "ERROR: failed to request that chip line is input." << std::endl;
            gpiod_line_release( pLine );
            gpiod_chip_close( pChip );
            break;
        }

        std::string val = std::to_string( gpiod_line_get_value( pLine ) );
        binaryStr = val + binaryStr;

        gpiod_line_release( pLine );
        gpiod_chip_close( pChip );
    }

    // translate string to unsigned int
    if( binaryStr.size( ) <= 0 ) {
        std::cerr << "ERROR: failed to extract value from chip: " << chipID << "." << std::endl;
        std::abort( );
    }
    
    retVal = static_cast< unsigned int >( std::stoi( binaryStr, nullptr, 2 ) );
    return retVal;
}

bool GPIOUtil::setFullValue( const unsigned int& chipID,
                             const unsigned int& width,
                             const unsigned int& value )
{
    bool retVal = true;
    unsigned int inputVal = value;
    for( int bit = 0; bit < width; ++bit ) {
        // open GPIO chip
        std::string chipPath = GPIO_DEV_CHIP_PATH + std::to_string( chipID );
        std::cout << "chip path :" << chipPath << std::endl;
        
        struct gpiod_chip* pChip = gpiod_chip_open( chipPath.c_str( ) );
        if( pChip == nullptr ) {
            std::cerr << "ERROR: failed to open GPIO chip: " << chipID << "." << std::endl;
            retVal = false;
            break;
        }

        struct gpiod_line* pLine = gpiod_chip_get_line( pChip, bit );
        if( pLine == nullptr ) {
            std::cerr << "ERROR: failed to open GPIO chip line: " << bit << "." << std::endl;
            gpiod_chip_close( pChip );
            retVal = false;
            break;
        }

        if( gpiod_line_request_output( pLine, "", 0 ) == -1 ) { // success: 0 and fail: -1
            std::cerr << "ERROR: failed to request that chip line is output." << std::endl;
            gpiod_line_release( pLine );
            gpiod_chip_close( pChip );
            retVal = false;
            break;
        }

        unsigned int bitVal = inputVal & 0x1;
        std::cout << "GPIO DAQ enable set value: " << bitVal << std::endl;
        if( gpiod_line_set_value( pLine, bitVal ) == -1 ) { // success: 0 and fail: -1
            std::cerr << "ERROR: failed to setvalue to chip line" << std::endl;
            gpiod_line_release( pLine );
            gpiod_chip_close( pChip );
            retVal = false;
            break;
        }
        inputVal >> 1;


        gpiod_line_release( pLine );
        gpiod_chip_close( pChip );
    }
    
    return retVal;
}
