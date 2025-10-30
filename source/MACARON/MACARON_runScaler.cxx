#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <cstdlib>
#include <cctype>
#include <algorithm>
#include <iomanip>
#include <unistd.h>
#include <time.h>
#include <dirent.h>
#include "GPIOUtil.h"

void         usage             ( );

int main( int argc, char** argv )
{
    // check arguments
    if( argc != 3 ) {
        std::cerr << "ERROR: mismatch the number of arguments." << std::endl;
        usage( );
        std::abort( );
    }

    // check directory
    std::string baseFilePath = argv[1];
    DIR* dp = opendir( baseFilePath.c_str( ) );
    if( dp == nullptr ) {
        std::cerr << "ERROR: target directory does not exist." << std::endl;
        usage( );
        std::abort( );
    }
    closedir( dp );

    // check period number
    std::string perNumStr = argv[2];
    if( std::all_of( perNumStr.cbegin( ), perNumStr.cend( ), isdigit ) == false ) {
        std::cerr << "ERROR: period number " << perNumStr << " is not digit." << std::endl;
        usage( );
        std::abort( );
    }

    unsigned int perNum = std::stoi( argv[2] );
    std::ostringstream sout;
    sout << std::setfill('0') << std::setw(4) << perNum;
    std::string perNumDir = "per" + sout.str( );

    std::string filePath = baseFilePath + "/";
    filePath += perNumDir;
    
    std::ofstream ofs( filePath );
    if( ofs.is_open( ) == false ) {
        std::cerr << "ERROR: failed to open " << filePath << " ." << std::endl;
        usage( );
        std::abort( );
    }

    time_t       unixtime;
    unsigned int cnt_store, trg_cnt_store, real_cnt_store, sw_re = 0;

    unsigned int sw_busy = 0;
    unsigned int sw_finRead = 0;

    unsigned int fileID = 0;
    bool isFirst = true;
    while( 1 ) {

        // check hardware status
        sw_re = GPIOUtil::getFullValue( CHIP_ID_SW_READ_ENABLE, WIDTH_SW_READ_ENABLE );
        if( sw_re == true ) {
            if( sw_finRead == 0 ) {
                time( &unixtime );
                if( isFirst == true ) {
                    sw_finRead = 1;
                    isFirst = false;
                    continue;
                }
                cnt_store = GPIOUtil::getFullValue( CHIP_ID_CNT_STORE, WIDTH_CNT_STORE );
                trg_cnt_store = GPIOUtil::getFullValue( CHIP_ID_TRG_CNT_STORE, WIDTH_TRG_CNT_STORE );
                real_cnt_store = GPIOUtil::getFullValue( CHIP_ID_REAL_CNT_STORE, WIDTH_REAL_CNT_STORE );

                std::ostringstream oss;
                oss << std::setfill('0') << std::setw(4) <<fileID;
                std::string fileIDStr = oss.str( );
                std::cout << fileIDStr      << "\t"
                          << real_cnt_store << "\t"
                          << cnt_store      << "\t"
                          << trg_cnt_store  << "\t"
                          << unixtime       << std::endl;

                ofs       << fileIDStr      << "\t"
                          << real_cnt_store << "\t"
                          << cnt_store      << "\t"
                          << trg_cnt_store  << "\t"
                          << unixtime       << std::endl;
                    
                sw_finRead = 1;
                ++fileID;
            }
        }
        else {
            sw_finRead = 0;
        }

        sw_busy = ( sw_re == 1 && sw_finRead == 0 ) ? 1 : 0;
        usleep( 100000 );
    }
    
    return 0;
}

void usage( )
{
    std::cout << "USAGE: ./runScaler [output path] [period number]" << std::endl;
    std::cout << "e.g. ) $ ./runScaler /nadb/nadb48/scaler/20220406/ 1" << std::endl;
    std::cout << std::endl;
    
    return;
}


