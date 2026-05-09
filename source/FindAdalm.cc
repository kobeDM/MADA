#include <iostream>
#include <libm2k/contextbuilder.hpp>
#include <libm2k/m2k.hpp>
#include <string>
#include <vector>

using namespace std;
using namespace libm2k;
using namespace libm2k::context;

int main( )
{
    try {
        std::vector<std::string> uris = context::getAllContexts( );

        if ( uris.empty( ) ) {
            cout << "No ADALM2000 devices found." << endl;
            return 0;
        }

        cout << "Detected ADALM2000 devices:" << endl;

        for ( const auto &uri : uris ) {
            M2k *ctx = m2kOpen( uri.c_str( ) );

            if ( !ctx ) {
                cerr << "Failed to open device at URI: " << uri << endl;
                continue;
            }

            string serial     = ctx->getSerialNumber( );
            string actual_uri = ctx->getUri( );

            cout << "----------------------------------" << endl;
            cout << "URI          : " << actual_uri << endl;
            cout << "Serial Number: " << serial << endl;

            contextClose( ctx );
        }

    } catch ( const std::exception &e ) {
        cerr << "Error: " << e.what( ) << endl;
        return 1;
    }

    return 0;
}