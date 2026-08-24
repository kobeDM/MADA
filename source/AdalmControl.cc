#include <getopt.h>

#include <chrono>
#include <thread>

#include "../include/AdalmUtil.h"

using namespace libm2k;
using namespace libm2k::analog;
using namespace libm2k::digital;  //for dio
using namespace libm2k::context;

const int channels[16] = {
    1,  // D0
    1,  // D1
    1,  // D2
    1,  // D3
    1,  // D4
    0,  // D5
    0,  // D6
    0,  // D7
    0,  // D8
    0,  // D9
    0,  // D10
    0,  // D11
    0,  // D12
    0,  // D13
    0,  // D14
    0   // D15
};
const double ANALOG_VOLTAGE = 3.3;

int main( int argc, char *argv[] )
{
    std::cout << "----Adalm Digital Output Control----" << std::endl;

    struct option longopts[] = {
        {"help",   no_argument,       NULL, 'h'},
        {"serial", required_argument, NULL, 's'},
        {"latch",  required_argument, NULL, 'l'},
        {"width",  required_argument, NULL, 'w'},
        {0,        0,                 0,    0  },
    };

    int         longindex;
    int         opt;
    std::string serialNumber = "";
    int         latch        = 0;
    double      width        = -1.0;  // <0: single latch (default), >=0: pulse mode (sec.)

    while ( ( opt = getopt_long( argc, argv, "hs:l:w:", longopts, &longindex ) ) != -1 ) {
        switch ( opt ) {
        case 's':
            serialNumber = optarg;
            break;

        case 'l':
            latch = std::stoi( optarg );
            break;

        case 'w':
            width = std::stod( optarg );
            break;

        case '?':
            std::cerr << "Error: invalid option or missing argument." << std::endl;
            return 1;

        case 'h':
        default:
            std::cerr << "Usage: " << argv[0] << " [OPTIONS]" << std::endl;
            std::cerr << "Options:" << std::endl;
            std::cerr << "  -h, --help             Show this help message" << std::endl;
            std::cerr << "  -s, --serial=SERIAL    Serial number" << std::endl;
            std::cerr << "  -l, --latch=LATCH      Latch (ignored if --width is given)" << std::endl;
            std::cerr << "  -w, --width=SECONDS    Output a single latch-up/down pulse of this width instead of a static latch" << std::endl;
            return 1;
        }
    }

    if ( serialNumber.empty( ) ) {
        std::cerr << "Error: serial number is required." << std::endl;
        return 1;
    }

    // serch for target ADALM
    std::cout << "Searching for ADALM" << std::endl;
    M2k *m2k = ConnectToAdalmWithSerial( serialNumber );
    if ( !m2k ) {
        std::cerr << serialNumber << " not found." << std::endl;
        return 1;
    }

    std::cout << "ADALM found: S/N: " << m2k->getSerialNumber( ) << std::endl;
    std::cout << "             URI: " << m2k->getUri( ) << std::endl;

    // set analog power output (kept on regardless of digital latch state)
    M2kAnalogOut *aout    = m2k->getAnalogOut( );
    const int     channel = 0;
    AnalogDcOut( aout, channel, ANALOG_VOLTAGE );

    // *** Digital output control *** //
    M2kDigital *dout = m2k->getDigital( );  // for digial io

    auto printDigitalOutput = []( const char *level ) {
        std::cout << "Digital output: " << std::endl;
        for ( int i = 0; i < 16; i++ ) {
            if ( channels[i] ) {
                std::cout << "D" << i << ": " << level << std::endl;
            }
        }
    };

    if ( width >= 0.0 ) {
        // *** Pulse mode: single latch-up/down cycle of the given width *** //
        std::cout << "**** Pulse mode: width " << width << " sec. ****" << std::endl;

        std::cout << "**** Latch up. ****" << std::endl;
        DigitalLatchUp( dout, channels );
        printDigitalOutput( "HIGH" );

        std::this_thread::sleep_for( std::chrono::duration<double>( width ) );

        std::cout << "**** Latch down. ****" << std::endl;
        DigitalLatchDown( dout, channels );
        printDigitalOutput( "LOW" );
    } else if ( latch ) {
        std::cout << "**** Latch up is selected. ****" << std::endl;
        DigitalLatchUp( dout, channels );
        printDigitalOutput( "HIGH" );
    } else {
        std::cout << "**** Latch down is selected. ****" << std::endl;
        DigitalLatchDown( dout, channels );
        printDigitalOutput( "LOW" );
    }

    return 0;
}