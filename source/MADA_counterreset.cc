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
#include <regex>
#include <sstream>
#include <stdio.h>
#include <string.h>
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

    int                      numperfile  = 1000;  // default numofevents per file
    int                      numperdir   = 10;    // default num of files per directory
    int                      maxnumADALM = 8;
    int                      f_index     = 0;
    int                      fopt        = 0;
    double                   dfreq[maxnumADALM];
    std::vector<std::string> MADALM_URI;
    std::vector<std::string> MADALM_SN;

    char          str_dummy[2];
    std::string   filename_head;
    struct option longopts[] = {
        {"help",              no_argument,       NULL, 'h'},
        {"Mbytesperfile",     required_argument, NULL, 'n'},
        {"numperdir",         required_argument, NULL, 'n'},
        {"filename_head",     required_argument, NULL, 'f'},
        {"verbose",           no_argument,       NULL, 'v'},
        {"slow_control_only", no_argument,       NULL, 's'},
        {0,                   0,                 0,    0  },
    };
    int  index;
    int  opt;
    int  longindex;
    int  numopt = 0;
    int  hopt   = 0;
    int  nopt   = 0;
    int  vopt   = 0;
    int  sopt   = 1;
    int  gopt   = 1;
    char filename[128];

    while ( ( opt = getopt_long( argc, argv, "shvn:m:f:", longopts, &longindex ) ) != -1 ) {
        switch ( opt ) {
        case 'h':
            hopt = 1;
            numopt++;
            break;
        case 'v':
            vopt = 1;
            numopt++;
            break;
        case 's':
            sopt = 1;
            numopt++;
            break;
        case 'n':
            nopt = 1;
            numopt += 2;
            numperfile = (atoi)( optarg ) << 20;
            break;
        case 'm':
            numopt += 2;
            numperdir = (atoi)( optarg );
            break;
        case 'f':
            nopt = 1;
            numopt += 2;
            filename_head = optarg;
            break;
        default:
            return 1;
        }
    }

    if ( hopt ) {
        printf( "MADA [-h || -help] [-n numperfile] [-m numperdir] [-c (control only]\n" );
        return 0;
    }
    if ( nopt ) {
    }

    std::cout << "----Loading config file ----" << std::endl;
    std::ifstream ifs( "MADA_config.json" );

    rapidjson::IStreamWrapper isw( ifs );
    rapidjson::Document       doc;
    doc.ParseStream( isw );
    if ( doc.HasParseError( ) ) {
        std::cout << "error offset:" << doc.GetErrorOffset( ) << std::endl;
        std::cout << "error parse:" << rapidjson::GetParseError_En( doc.GetParseError( ) ) << std::endl;
    }

    const rapidjson::Value &ol = doc["general"];
    if ( !doc["general"].IsObject( ) ) {
        std::cout << "general is not a json Object. Check the config file." << std::endl;
        return 1;
    }
    std::cout << "==general configs==" << std::endl;
    for ( rapidjson::Value::ConstMemberIterator itrgl = ol.MemberBegin( ); itrgl != ol.MemberEnd( ); itrgl++ ) {
    }

    if ( !sopt && gopt ) {
        int                     ADALMid = 0;
        const rapidjson::Value &o       = doc["ADALM"];
        if ( !doc["ADALM"].IsObject( ) ) {
            std::cout << "ADALM is not a json Object. Check the config file." << std::endl;
            return 1;
        }
        std::string thisMADALM = "MADALM_0";
        std::cout << "==ADALM configs==" << std::endl;
        for ( rapidjson::Value::ConstMemberIterator itr = o.MemberBegin( ); itr != o.MemberEnd( ); itr++ ) {
            const char *name = itr->name.GetString( );
            std::cout << name << ": ";
            if ( name == thisMADALM ) {
                const rapidjson::Value &oo = itr->value;
                MADALM_URI.insert( MADALM_URI.begin( ) + ADALMid, oo["URI"].GetString( ) );
                MADALM_SN.insert( MADALM_SN.begin( ) + ADALMid, oo["S/N"].GetString( ) );
                dfreq[ADALMid] = oo["Clock_d"].GetDouble( );
                std::cout << "URI: " << MADALM_URI[ADALMid];
                std::cout << " S/N: " << MADALM_SN[ADALMid] << std::endl;
                std::cout << "\tClock(D): " << std::scientific << std::setprecision( 1 ) << dfreq[ADALMid] << " Hz" << std::dec << std::endl;
                ADALMid++;
            }
        }
        int numADALM = ADALMid;

        std::cout << "----Loading config file, done. ----" << std::endl;

        // read adalm configurations ends
        M2k        *MADALM[numADALM];
        M2kDigital *dMADALM[numADALM];

        // initial message
        if ( sopt )
            std::cout << "\trun-control only" << std::endl;
        else {
            std::cout << "with data aquisition." << std::endl;
            std::cout << "\t" << std::scientific << std::setprecision( 2 ) << double( numperfile ) << " bytes will be recorded." << std::endl;
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
        std::cout << "----Initializing ADALM boards, done ----" << std::endl;
        if ( sopt )
            numperdir = 1;

        // data taking
        ad_d_latch_up( dMADALM[0] );

        if ( sopt ) {
            std::cout << "\n" << std::endl;
            std::cout << "return to finish>" << std::endl;
            std::cin.getline( str_dummy, sizeof( str_dummy ) );
        }

        ad_d_latch_down( dMADALM[0] );
    }

    return 0;
}
