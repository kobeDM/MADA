#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include "RBCP.h"
#include "SiTCP.h"
#include <unistd.h>
using namespace std;

int main( int argc, char* argv[] )
{
    if( argc != 4 && argc != 5 ) {
        std::cerr << " USAGE> MADA_VthScan [IP address] [Vth min] [Vth max] [scan step] " << std::endl;
        std::cerr << "   Vth: give a decimal number from 0 and 16383 "                    << std::endl;
        std::cerr << "        this program scan Vth from [start Vth] "                    << std::endl;
        std::cerr << "        to [end Vth] with the pitch of [delta-Vth]"                 << std::endl;
        std::cerr << "        default value of [delta-Vth] is 100 in decimal"             << std::endl;
        exit( 1 );
    }

    std::string ip_address = argv[1];
    int Vth_min = atoi( argv[2] );
    if( Vth_min > 0x3fff ) Vth_min = 0x3fff;

    int Vth_max = atoi( argv[3] );
    if( Vth_max > 0x3fff ) Vth_max = 0x3fff;

    int step = 100;
    if (argc > 4) {
        step = atoi( argv[4] );
        if( step > 0x3fff ) step = 0x3fff;
    }

    std::string outfile_config_name = "scan_config.out";
    std::ofstream outfile_config;
    outfile_config.open( outfile_config_name.c_str( ), std::ios::out );
    outfile_config << "IP: " << ip_address << std::endl;
    outfile_config << "Vth(lower): " << Vth_min << std::endl;
    outfile_config << "Vth(upper): " << Vth_max << std::endl;
    outfile_config << "Vth(step): " << step << std::endl;
    outfile_config.close( );

    std::cout << "before SiTCP socket open" << std::endl;

    RBCP SlowCtrl;
    SiTCP EtherData;
    SlowCtrl.Open( ip_address );
    EtherData.Open( ip_address );

    std::cout << "after SiTCP socekt open" << std::endl;

    for( int Vth = Vth_min; Vth <= Vth_max; Vth += step ) {
        if( Vth > 0x3fff ) break;

        // Set Vth
        char cmd[256];
        cmd[0] = ( Vth >> 8 ) & 0x3f;
        cmd[1] = Vth & 0xff;

        SlowCtrl.WriteRBCP( 0x80, cmd, 2 );

        cmd[0] = 0x01;
        SlowCtrl.WriteRBCP( 0xf0, cmd, 1 );
        sleep( 1 );
        std::cout << std::dec;
        std::cout << " Vth : " << Vth;

        int data_size = 0;
        char c_data[4096];

        std::cout << " refreshing buffer..." << std::flush;
        while( true ) {
            int num = EtherData.Read( c_data );
            if( num > 0 ) data_size += num;

            if( data_size > 0x20000 ) break;
        }
        std::cout << " done" << '\n' << std::flush;

        char filename[100];
        sprintf( filename, "Vth_%04x.scn", Vth );
        ofstream OutData( filename, ios::out );

        int e_index = 0;
        data_size = 0;
        while( true ) {
            std::cout << std::hex;
            std::cout << " data reading...   " << data_size << '\r' << std::flush;

            int num = EtherData.Read( c_data );
            if( num > 0 ) {
                OutData.write( c_data, num );
                data_size += num;
            }
            if( c_data[num - 4] == 'u' && c_data[num - 3] == 'P' &&
                c_data[num - 2] == 'I' && c_data[num - 1] == 'C' )
                e_index++;

            if( data_size > 0x100000 || e_index > 1e3 ) break;
        }

        std::cout << "                                            " << '\r' << std::flush;
        OutData.close( );
    }

    return 0;
}
