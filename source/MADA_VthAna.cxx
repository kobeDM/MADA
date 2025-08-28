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
#include <TCanvas.h>
#include <TStyle.h>
#include <TROOT.h>
#include <TMath.h>
#include <TLine.h>
#include <arpa/inet.h>

int main( int argc, char* argv[] ){

    if( argc !=5 && argc != 6 ) {
        std::cerr << " USAGE> MADA_VthAna [data dir.] [IP address] [Vth min] [Vth max] [scan step] " << std::endl;
        exit( 1 );
    }
    
    std::string dirname = argv[1];
    std::string ip_address = argv[2];
    int Vth_min = atoi( argv[3] );
    if( Vth_min > 0x3fff ) Vth_min = 0x3fff;

    int Vth_max = atoi( argv[4] );
    if( Vth_max > 0x3fff ) Vth_max = 0x3fff;

    int step = 100;
    if( argc > 4 ) {
        step = atoi( argv[5] );
        if( step > 0x3fff ) step = 0x3fff;
    }

    int Nbin = ( Vth_max - Vth_min ) / step + 2;
    double* y_bin = new double [Nbin];
    for( int i = 0; i < Nbin; i++ ) y_bin[i] = Vth_min + i * step;

    std::string figtitle = "Vth survey (" + dirname + ")";
    std::cout << figtitle << std::endl;
    TH2F* DAC_image = new TH2F( "DAC_image", figtitle.c_str(), 130, -1.5, 128.5, Nbin-1, y_bin );
  
    for( int fi = Vth_min; fi <= Vth_max; fi += step ) {
        std::string filename = Form( "%s/Vth_%04x.scn", dirname.c_str(), fi );
        std::cout << y_bin[fi/step] <<":\t" << filename << '\n' << std::flush;
        
        int event_num = 0;
        double total[128] = { 0.0 };
        std::ifstream data_file( filename );
        if( data_file.is_open( ) == false ) {
            std::cerr << "Failed to open " << filename << std::endl;
            break;
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
                        if( ( data & 0xff ) == 0x64 ) { // header read end
                            double count[128] = { 0.0 };
	      
                            int i_data;
                            data_file.read( (char*)&i_data, sizeof( int ) ); // skip Event counter
                            data_file.read( (char*)&i_data, sizeof( int ) ); // skip clock counter

                            data_file.read( (char*)&i_data, sizeof( int ) ); // skip input ch2 counter
                            if( htonl( i_data ) != 0x75504943 ) { // check if packet trailer (seems to be redundant)
                                for( int i=0; i < 2*511; i++ ) data_file.read( (char*)&i_data, sizeof( int ) ); // skip ADC

                                data_file.read( (char*)&i_data, sizeof( int ) ); // skip version
                                data_file.read( (char*)&i_data, sizeof( int ) ); // skip encode clock

                                // Hit data
                                for(;;) {
                                    data_file.read( (char*)&i_data, sizeof( int ) ); // hit header
                                    if( htonl( i_data ) == 0x75504943 || data_file.eof( ) ) break;

                                    for( int i = 0; i < 4; i++ ) {
                                        data_file.read( (char*)&i_data, sizeof( int ) ); // hits for 128 channel (32ch per loop)
                                        i_data = htonl( i_data );

                                        for( int strip = 0; strip < 32; strip++ )
                                            if( ( i_data >> strip ) & 0x1 ) count[32*(3-i) + strip] += 1;
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
            for( int st = 0; st < 128; st++ )
                DAC_image->Fill( st, fi, static_cast< double >( total[st] )/static_cast< double >( event_num ) );
        }
    }

    std::string ofilename = Form( "%s/Vth.root", dirname.c_str( ) );
    TFile rootFile( ofilename.c_str( ), "recreate" );
    DAC_image->SetDirectory( &rootFile );
    DAC_image->Write( );

    TCanvas cvs( "cvs", "cvs", 800, 600 );
    DAC_image->GetZaxis( )->SetRangeUser( 0.0, 1.2 );
    DAC_image->SetTitle( Form( "Vth scan ( %s, %s)", dirname.c_str( ), ip_address.c_str( ) ) );
    DAC_image->Draw( "colz" );

    double current_Vth = ( Vth_max + Vth_min ) * 0.5;
    TLine line(0.0, current_Vth, 128.0, current_Vth );
    line.SetLineColor( 2 );
    line.SetLineWidth( 4 );
    line.Draw( "same" );
    cvs.SaveAs( Form( "%s/Vthcheck.png", dirname.c_str( ) ) );

    rootFile.Close( );
    std::cout << "written in " << ofilename << std::endl;

    return 0;
}
