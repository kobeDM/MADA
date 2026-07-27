#include "../include/AdalmUtil.h"

int OUTPUT_CH = 0;

int main( int argc, char *argv[] )
{
    std::cout << "----Adalm Test Pulse Control----" << std::endl;

    if ( argc != 5 ) {
        std::cerr << "Usage: " << argv[0] << " [SERIAL] [I/O] [VOLTAGE (V)] [FREQUENCY (Hz)]" << std::endl;
        return 1;
    }

    std::string serialNumber = argv[1];
    int         io           = std::stoi( argv[2] );
    double      voltage      = std::stod( argv[3] );
    double      frequency    = std::stod( argv[4] );
    std::cout << "Serial   : " << serialNumber << std::endl;
    std::cout << "I/O      : " << io << std::endl;
    std::cout << "Voltage  : " << voltage << " V" << std::endl;
    std::cout << "Frequency: " << frequency << " Hz" << std::endl;

    // serch for target ADALM
    std::cout << "--- Searching for ADALM ---" << std::endl;
    M2k *m2k = ConnectToAdalmWithSerial( serialNumber );
    if ( !m2k ) {
        std::cerr << serialNumber << " not found." << std::endl;
        return 1;
    }

    std::cout << "ADALM found: S/N: " << m2k->getSerialNumber( ) << std::endl;
    std::cout << "             URI: " << m2k->getUri( ) << std::endl;

    // *** Analog power output control *** //
    if ( io == 1 ) {
        std::cout << "Outputting square wave: voltage " << voltage << " V, frequency " << frequency << " Hz" << std::endl;
        M2kAnalogOut *aout = m2k->getAnalogOut( );
        OutputWaveformSquare( aout, OUTPUT_CH, voltage, frequency );
        return 0;
    } else if ( io == 0 ) {
        std::cout << "Killing output" << std::endl;
        DisconnectAdalm( m2k );
        return 0;
    } else {
        std::cerr << "Error: invalid I/O type. Use 0 for DC output or 1 for square wave output." << std::endl;
        return 1;
    }
}