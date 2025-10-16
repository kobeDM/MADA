#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include "RBCP.h"
#include "SiTCP.h"
#include <unistd.h>

const int TIMEOUT_SEC = 100000;

int main( int argc, char* argv[] )
{
    if( argc != 3 ) {
        std::cerr << " USAGE> SetDAC [IP address] [Vth val.] " << std::endl;
        std::cerr << "   Vth: give a decimal number from 0 and 16383 " << std::endl;
        exit(1);
    }

    std::string ip_address = argv[1];
    int Vth = atoi( argv[2] ) & 0x3fff;

    std::string outfile_config_name = "DACsurvey_config.out";
    std::ofstream outfile_config;
    outfile_config.open( outfile_config_name.c_str( ), std::ios::out );
    outfile_config << "IP: " << ip_address << std::endl;
    outfile_config << "Vth: " << Vth << std::endl;
    outfile_config.close( );

    RBCP SlowCtrl;
    SiTCP EtherData;
    SlowCtrl.Open( ip_address );
    EtherData.Open( ip_address );

    // Set Vth
    char cmd[256];
    cmd[0] = ( Vth >> 8 ) & 0x3f;
    cmd[1] = Vth & 0xff;
    SlowCtrl.WriteRBCP( 0x80, cmd, 2 );

    cmd[0] = 0x01;
    SlowCtrl.WriteRBCP( 0xf0, cmd, 1 );
    sleep( 1 );
    std::cout << " Vth set at " << Vth << std::endl;
    std::cout << "DAC survey start" << std::endl;

    // DAC survey
    for( int i = 0; i < 64; i++ ) {
        // DAC Set
        for( int ch = 0; ch < 128; ch++ ) {
            cmd[ch] = SlowCtrl.convDAC( i, 0, 0 );
        }

        SlowCtrl.WriteRBCP( 0, cmd, 128 );
        cmd[0] = 0x02;
        SlowCtrl.WriteRBCP( 0xf0, cmd, 1 );
        sleep( 1 );
        int data_size = 0;
        char c_data[4096];
        while( true ) {
            int num = EtherData.Read( c_data, TIMEOUT_SEC );
            if( num > 0) data_size += num;
            else         break;

            if( data_size > 0x20000 ) break;
        }

        char filename[100];
        sprintf( filename, "DAC_%02d_%04x.srv", i, Vth );
        std::ofstream OutData( filename, std::ios::out );

        int e_index = 0;
        int max_e_index = 100;
        data_size = 0;
        // int max_count = 10;
        // int count = 0;

        while( true ) {
            // count++;
            int num = EtherData.Read( c_data );
            if( num > 0 ) {
                OutData.write( c_data, num );
                data_size += num;
            }

            // if( c_data[num - 4] == 'u' && c_data[num - 3] == 'P' && c_data[num - 2] == 'I' && c_data[num - 1] == 'C' )
            //     e_index++;
            // std::cout << " DAC value: " << std::dec << i << "/64: \r" << std::flush;

            // if( data_size > 0x80000 || e_index > 1e3 || count > max_count ) break;

            for( int i=0; i < num-3; ++i )
                if( c_data[i]   == 'u' && c_data[i+1] == 'P' && c_data[i+2] == 'I' && c_data[i+3] == 'C')
                    e_index += 1;

            if( e_index > max_e_index ) break;
        }

        OutData.close();
    }

    return 0;
}
