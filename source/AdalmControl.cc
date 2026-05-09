#include <getopt.h>

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
    0,  // D4
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
        {0,        0,                 0,    0  },
    };

    int         longindex;
    int         opt;
    std::string serialNumber = "";
    int         latch        = 0;

    while ( ( opt = getopt_long( argc, argv, "hs:l:", longopts, &longindex ) ) != -1 ) {
        switch ( opt ) {
        case 's':
            serialNumber = optarg;
            break;

        case 'l':
            latch = std::stoi( optarg );
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
            std::cerr << "  -l, --latch=LATCH      Latch" << std::endl;
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

    // *** Analog power output control *** //
    double voltage = 0.0;
    if ( latch ) {
        std::cout << "**** Latch up is selected. ****" << std::endl;
    } else {
        std::cout << "**** Latch down is selected. ****" << std::endl;
    }
    voltage = ANALOG_VOLTAGE;

    // set analog power output
    M2kAnalogOut *aout    = m2k->getAnalogOut( );
    const int     channel = 0;
    AnalogDcOut( aout, channel, voltage );

    // *** Digital output control *** //
    M2kDigital *dout = m2k->getDigital( );  // for digial io

    if ( latch ) {
        std::cout << "**** Latch up is selected. ****" << std::endl;
        DigitalLatchUp( dout, channels );
        std::cout << "Digital output: " << std::endl;
        for ( int i = 0; i < 16; i++ ) {
            if ( channels[i] ) {
                std::cout << "D" << i << ": HIGH" << std::endl;
            }
        }
    } else {
        std::cout << "**** Latch down is selected. ****" << std::endl;
        DigitalLatchDown( dout, channels );
        std::cout << "Digital output: " << std::endl;
        for ( int i = 0; i < 16; i++ ) {
            if ( channels[i] ) {
                std::cout << "D" << i << ": LOW" << std::endl;
            }
        }
    }

    return 0;
}