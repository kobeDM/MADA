#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include <string>
#include <fstream>
#include <TH1F.h>
#include <TH2F.h>
#include <TF1.h>
#include <TFile.h>
#include <TRint.h>
#include <TMath.h>
#include <arpa/inet.h>
#include <TROOT.h>
#include <TSystem.h>
#include <TStyle.h>
#include <TCanvas.h>
#include <TPad.h>
#include <TH2F.h>
#include <TLatex.h>
#include "TApplication.h"


int main( int argc, char *argv[] )
{
    if( argc != 4 ) {
        std::cerr << " USAGE> DAC_Analysis [data dir.] [Vth val.] [IP(least 8bits)]" << std::endl;
        std::cerr << "  Vth: give a decimal number from 0 and 16383 " << std::endl;
        exit(1);
    }

    std::string dirname = argv[1];
    int Vth = atoi(argv[2]) & 0x3fff;
    int IP = atoi(argv[3]);
    bool isAnode = ( IP < 24 ) ? true : false;

    std::string outfile_config_name = "DAC_ana_config.out";
    std::ofstream outfile_config;
    outfile_config.open( outfile_config_name.c_str( ), std::ios::out );
    outfile_config << dirname << std::endl;
    outfile_config.close( );

    std::string figtitle = "DAC survey (" + dirname + ")";
    TH2F* DAC_image = new TH2F("DAC_image", figtitle.c_str( ), 130, -1.5, 128.5, 64, -0.5, 63.5 );
    std::cout << "IP=192.168.100." << IP << std::endl << std::flush;
    for( int fi = 0; fi < 64; fi++ ) {
        std::string filename = Form( "%s/DAC_%02d_%04x.srv", dirname.c_str( ), fi, Vth );
        std::cout << filename << '\r' << std::flush;

        int event_num = 0;
        double total[128] = {0};
        std::ifstream data_file( filename );
        if( data_file.is_open( ) == false ) {
            std::cerr << "Failed to open " << filename << std::endl;
            exit( 1 );
        }

        while( data_file ) {
            char data;
            data_file.read( &data, 1 );
            if( data_file.eof( ) ) break;

            if( ( data & 0xff ) == 0xeb ) { // header read begin
                data_file.read( &data, 1 );
                if( ( data & 0xff ) == 0x90 ) {
                    data_file.read( &data, 1 );
                    if( ( data & 0xff ) == 0x19 ) {
                        data_file.read( &data, 1 );
                        if( ( data & 0xff ) == 0x64 ) {
                            double count[128] = { 0.0 };
                            int i_data = 0;
                            data_file.read( (char*)&i_data, sizeof( int ) ); // skip Event counter
                            data_file.read( (char*)&i_data, sizeof( int ) ); // skip clock counter
                            data_file.read( (char*)&i_data, sizeof( int ) ); // skip input ch2 counter
                            if( htonl( i_data ) != 0x75504943 ) { // check if packet trailer (seems to be redundant)
                                for( int i=0; i < 2*511; i++ ) data_file.read( (char*)&i_data, sizeof( int ) ); // skip ADC

                                data_file.read( (char*)&i_data, sizeof( int ) ); // skip version
                                data_file.read( (char*)&i_data, sizeof( int ) ); // skip encode clock

                                // Hit data
                                for( ;; ) {
                                    data_file.read( (char*)&i_data, sizeof( int ) ); // hit header
                                    if( htonl( i_data ) == 0x75504943 || data_file.eof( ) ) break;

                                    for( int i = 0; i < 4; i++ ) {
                                        data_file.read( (char *)&i_data, sizeof( int ) ); // hits for 128 channel (32ch per loop)
                                        i_data = htonl( i_data );

                                        for( int strip = 0; strip < 32; strip++ )
                                            if( ( i_data >> strip ) & 0x1 ) count[32 * (3 - i) + strip] += 1;
                                    }
                                }

                                for( int strp = 0; strp < 128; strp++ )
                                    total[strp] += static_cast< double >( count[strp] ) / 1024.0;
                                event_num++;
                            }
                        }
                    }
                }
            }
        }
        data_file.close( );

        if( event_num != 0 ) {
            for( int st = 0; st < 128; st++ ) {
                double rate = total[st] / static_cast< double >( event_num );
                if(rate > 2) rate = 0;
                DAC_image->Fill( st, fi, rate );
            }
        }
    }
    
    TFile rootFile( Form( "%s/DAC.root", dirname.c_str( ) ), "recreate" );
    DAC_image->SetDirectory( &rootFile );
    DAC_image->Write();
    
    TCanvas cvs( "cvs", "cvs", 800, 600 );
    DAC_image->Draw( "colz" );
    cvs.SaveAs( Form( "%s/DAC_image.png", dirname.c_str( ) ) );
    
    std::ofstream DacOut( Form( "%s/base_correct.dac", dirname.c_str( ) ), std::ios::out );
    TH1F *proj = new TH1F( "proj", "", 64, -0.5, 63.5 );
    TF1 *erf = new TF1( "erf", "[0] * TMath::Erf((x-[1])/[2])+[3]" );
    erf->SetParLimits( 1, 0, 64 );
    TCanvas *ViewWin = new TCanvas( "ViewWin", "", 0, 0, 800, 600 );
    ViewWin->SetGridx( );
    ViewWin->SetGridy( );
    ViewWin->Draw( );
    double fit_min = 2.0;
    double fit_max = 61.0;

    for( int strip = 0; strip < 128; strip++ ) {
        for( int dac = 0; dac < 64; dac++ ) proj->SetBinContent( dac + 1, DAC_image->GetBinContent( strip + 2, dac + 1 ) );
        std::string histname = Form( "%s/Ch %03d", dirname.c_str( ), strip );
        proj->SetTitle( histname.c_str( ) );
        proj->SetMaximum(1);
        proj->SetMinimum(0);

        erf->SetParLimits( 1, fit_min, fit_max );
        erf->SetParLimits( 2, 0,60 );
        erf->SetParLimits( 3, 0,1 );
        if( isAnode == true ) {
            erf->SetParameters( -0.5, 32, 5, 0.5 );
            erf->SetParLimits( 0,-1,0 );
        }
        else{
            erf->SetParameters( 0.5, 32, 5, 0.5 );
            erf->SetParLimits( 0, 0,1 );
        }

        proj->Fit( "erf", "", "", fit_min, fit_max );
        proj->Draw( );

        int DACval = TMath::FloorNint( proj->GetFunction( "erf" )->GetParameter( 1 ) + 0.5 );
        if     ( DACval < 0  ) DACval = 2;
        else if( DACval > 63 ) DACval = 61;
        
        double rate = TMath::Abs( proj->GetFunction( "erf" )->GetParameter( 0 ) );
        double offset = TMath::Abs( proj->GetFunction( "erf" )->GetParameter( 3 ) );
        if( rate < 0.2 && offset > 0.5 ) //all yellow
            DACval = isAnode ? fit_min : fit_max;
        else if( rate < 0.2 && offset < 0.2 )  //all blue
            DACval = isAnode ? fit_max : fit_min;

        std::vector< std::string > par_str_arr;
        par_str_arr.reserve( 4 );
        for( int i = 0; i < 4; i++ )
            par_str_arr.push_back( Form( "par[%d]=%f", i, proj->GetFunction( "erf" )->GetParameter( i ) ) );
    
        TText* p0t = new TText( 20, 0.7, par_str_arr.at( 0 ).c_str( ) );
        TText* p1t = new TText( 20, 0.6, par_str_arr.at( 1 ).c_str( ) );
        TText* p2t = new TText( 20, 0.5, par_str_arr.at( 2 ).c_str( ) );
        TText* p3t = new TText( 20, 0.4, par_str_arr.at( 3 ).c_str( ) );

        std::string DACval_str = Form( "DAC value=%d", DACval );
        TText* t = new TText (40, 0.85, DACval_str.c_str( ) );
        p0t->Draw( );
        p1t->Draw( );
        p2t->Draw( );
        p3t->Draw( );
        t->Draw( );
        ViewWin->Update( );
        DacOut << strip << '\t' << DACval << std::endl;

        ViewWin->SaveAs( Form( "%s.png", histname.c_str( ) ) );
    }

    rootFile.Close();
    
    return 0;
}
