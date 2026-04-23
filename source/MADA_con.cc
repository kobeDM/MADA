#define _USE_MATH_DEFINES
#include "rapidjson/document.h"
#include "rapidjson/error/en.h"
#include "rapidjson/istreamwrapper.h"
#include <fstream>
#include <getopt.h>
#include <iomanip>
#include <iostream>
#include <libm2k/analog/m2kanalogin.hpp>
#include <libm2k/analog/m2kanalogout.hpp>
#include <libm2k/analog/m2kpowersupply.hpp>
#include <libm2k/contextbuilder.hpp>
#include <libm2k/digital/m2kdigital.hpp>  //for dio
#include <libm2k/m2k.hpp>
#include <math.h>
#include <sstream>
#include <stdio.h>
#include <string>
#include <sys/time.h>
#include <thread>
#include <unistd.h>

#include "MADA_ad.h"

using namespace libm2k;
using namespace libm2k::analog;
using namespace libm2k::digital;  // for dio
using namespace libm2k::context;

// uncomment the following definition to test triggering
#define TRIGGERING

int main( int argc, char *argv[] )
{

    printf( "MADA: Miraclue Argon DAQ\n" );

    int numperfile  = 1000;  // default numofevents per file
    int maxnumADALM = 8;

    // should be read from config file
    double                   dfreq[maxnumADALM];
    std::vector<std::string> MADALM_URI;
    std::vector<std::string> MADALM_SN;
    std::vector<std::string> gigaIwaki_IP;
    std::vector<std::string> gigaIwaki_DAC;
    std::vector<int>         gigaIwaki_Vth;
    // should be read from config file end

    char str_dummy[2];

    // option handling
    struct option longopts[] = {
        {"help",    no_argument,       NULL, 'h'},
        {"num",     required_argument, NULL, 'n'},
        {"verbose", no_argument,       NULL, 'v'},
        {0,         0,                 0,    0  },
    };
    int index;
    int opt;
    int longindex;
    int numopt = 0;
    int hopt   = 0;
    int nopt   = 0;
    int vopt   = 0;
    int copt   = 1;
    int gopt   = 1;

    while ( ( opt = getopt_long( argc, argv, "hgvn:", longopts, &longindex ) ) != -1 ) {
        switch ( opt ) {
        case 'h':
            hopt = 1;
            numopt++;
            break;
        case 'v':
            vopt = 1;
            numopt++;
            break;
        case 'n':
            nopt = 1;
            numopt += 2;
            numperfile = (atoi)( optarg );
            break;
        case 'g':
            copt = 1;
            numopt += 1;
            break;
        default:
            return 1;
        }
    }

    if ( hopt ) {
        printf( "MADA [-h || -help] [-n numperfile] [-c (control only]\n" );
        return 0;
    }
    if ( nopt ) {
    }
    // option handling end

    std::cout << "----Loading config file ----" << std::endl;
    std::ifstream ifs( "MADA_config.json" );

    rapidjson::IStreamWrapper isw( ifs );
    rapidjson::Document       doc;

    doc.ParseStream( isw );
    if ( doc.HasParseError( ) ) {
        std::cout << "error offset:" << doc.GetErrorOffset( ) << std::endl;
        std::cout << "error parse:" << rapidjson::GetParseError_En( doc.GetParseError( ) ) << std::endl;
    }

    // read general configurations
    const rapidjson::Value &ol = doc["general"];
    if ( !doc["general"].IsObject( ) ) {
        std::cout << "general is not a json Object. Check the config file." << std::endl;
        return 1;
    }
    std::cout << "==general configs==" << std::endl;

    for ( rapidjson::Value::ConstMemberIterator itrgl = ol.MemberBegin( ); itrgl != ol.MemberEnd( ); itrgl++ ) {
    }
    int                     ADALMid = 0;
    const rapidjson::Value &o       = doc["ADALM"];
    if ( !doc["ADALM"].IsObject( ) ) {
        std::cout << "ADALM is not a json Object. Check the config file." << std::endl;
        return 1;
    }

    std::cout << "==ADALM configs==" << std::endl;
    for ( rapidjson::Value::ConstMemberIterator itr = o.MemberBegin( ); itr != o.MemberEnd( ); itr++ ) {
        const char *name = itr->name.GetString( );
        std::cout << name << ": ";
        const rapidjson::Value &oo = itr->value;
        MADALM_URI.insert( MADALM_URI.begin( ) + ADALMid, oo["URI"].GetString( ) );
        MADALM_SN.insert( MADALM_SN.begin( ) + ADALMid, oo["S/N"].GetString( ) );
        dfreq[ADALMid] = oo["Clock_d"].GetDouble( );
        std::cout << "URI: " << MADALM_URI[ADALMid];
        std::cout << " S/N: " << MADALM_SN[ADALMid] << std::endl;
        std::cout << "\tClock(D): " << std::scientific << std::setprecision( 1 ) << dfreq[ADALMid] << " Hz" << std::dec << std::endl;
        ADALMid++;
    }
    int numADALM = ADALMid;

    std::cout << "----Loading config file, done. ----" << std::endl;

    // read adalm configurations ends

    M2k        *MADALM[numADALM];
    M2kDigital *dMADALM[numADALM];

    // initial message
    if ( copt )
        std::cout << "\trun-control only" << std::endl;
    else {
        std::cout << "with data aquisition." << std::endl;
        printf( "%d events per file will be recorded.\n", numperfile );
    }
    std::cout << "----Initializing ADALM boards ----" << std::endl;
    // ADALMs initilization
    for ( int i = 0; i < numADALM; i++ ) {
        std::cout << "\tInitializing MNADALM_" << i;
        MADALM[i] = m2kOpen( MADALM_URI[i].c_str( ) );
        if ( vopt )
            ad_showIDs( MADALM[i] );
        dMADALM[i] = MADALM[i]->getDigital( );  // for digial io
        ad_d_setClock( dMADALM[i], dfreq[i] );
        ad_d_init( dMADALM[i] );
        std::cout << ", ok" << std::endl;
    }
    ad_d_cyclic( dMADALM[1], false );

    std::cout << "----Initializing ADALM boards, done ----" << std::endl;

    ad_d_pulse( dMADALM[1], 15 );
    ad_d_latch_up( dMADALM[0] );

    int f_index = 0;

    printf( "\n" );
    printf( "carriage return>" );
    scanf( "%1[^\n]", str_dummy );

    ad_d_latch_down( dMADALM[0] );
    return 0;
}
