#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include "RBCP.h"
#include "SiTCP.h"
#include <unistd.h>

const int TIMEOUT_SEC = 1;

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

    char tmp_data[4096];
    int data_size = 0;
    std::cout << " refreshing buffer..." << std::flush;
    while( true ) {
        int num = EtherData.Read( tmp_data, TIMEOUT_SEC );
        if( num <= 0 ) break; // assuming that software veto will successfully be running
        else           data_size += num;

        if( data_size > 0x20000 ) break;
    }
    std::cout << " done" << '\n' << std::flush;

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

        char filename[100];
        sprintf( filename, "DAC_%02d_%04x.srv", i, Vth );
        std::ofstream OutData( filename, std::ios::out );

        char c_data[4096];
        int e_index = 0;
        int max_e_index = 400;
        while( true ) {
            int num = EtherData.Read( c_data );
            if( num > 0 )
                OutData.write( c_data, num );

            for( int i=0; i < num-3; ++i )
                if( c_data[i]   == 'u' && c_data[i+1] == 'P' && c_data[i+2] == 'I' && c_data[i+3] == 'C')
                    e_index += 1;

            cout << setw(6) << e_index << "/" << setw(6) << max_e_index << " counts stored\r";
            if( e_index > max_e_index ) break;
        }

        OutData.close();
    }

    return 0;
}
