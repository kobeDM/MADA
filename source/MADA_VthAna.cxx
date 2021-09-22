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
#include <TRint.h>
#include <TStyle.h>
#include <TROOT.h>
#include <TMath.h>
#include <arpa/inet.h>

using namespace std;

int main(int argc, char *argv[]){
  if(argc!=4 && argc!=5){
    cerr << " USAGE> DAC_Analysis [data dir.] [start Vth] [end Vth] [delta]" 
	 << endl;
    exit(1);
  }
  string dirname = argv[1];
  //  int s_Vth = atoi(argv[2]) & 0x3fff;
  int s_Vth = atoi(argv[2]);
  if(s_Vth>0x3fff)s_Vth=0x3fff;
  //  int e_Vth = atoi(argv[3]) & 0x3fff;
  int e_Vth = atoi(argv[3]);
  if(e_Vth>0x3fff)e_Vth=0x3fff;
  int delta = 100;
  if(argc>4){
    delta = atoi(argv[4]);
    if(delta>0x3fff)delta=0x3fff;
  }
  TRint app("app", &argc, argv);
  gStyle->SetOptStat(0);

  int Nbin = (e_Vth - s_Vth)/delta + 2;
  double *y_bin = new double [Nbin];
  for(int i=0; i<Nbin; i++){
    y_bin[i] = s_Vth + i * delta;
    //    cout << y_bin[i] << endl;
  }
  string figtitle="Vth survey ("+dirname+")";
  cout << figtitle<<endl;
  //  string figtitle = dirname;
  //    TH2F *DAC_image = new TH2F("DAC_image", "DAC Survey",
  ///                         130, -1.5, 128.5, Nbin-1, y_bin);
  TH2F *DAC_image = new TH2F("DAC_image", figtitle.c_str(),
                             130, -1.5, 128.5, Nbin-1, y_bin);
  
  for(int fi=s_Vth; fi<=e_Vth; fi+=delta){
    char filename[100];
    sprintf(filename, "%s/Vth_%04x.scn",dirname.c_str(), fi);
    //    dirname.push_back(filename);
    //    sprintf(filename, "Vth_%04x.scn", fi);
    cout << y_bin[fi/delta] <<":\t" ;
    cout << filename << '\n' << flush;

    double event_num=0;
    double total[128]={0};
    ifstream data_file(filename);
    if(!data_file){
      cerr << " Can't find " << filename << endl;
      break;
    }

    while(data_file){
      char data;
      data_file.read(&data, 1);
      if(data_file.eof())
        break;
      
      if((data & 0xff) == 0xeb){
        data_file.read(&data, 1);
        if((data & 0xff) == 0x90){
          data_file.read(&data, 1);
          if((data & 0xff) == 0x19){
            data_file.read(&data, 1);
            if((data & 0xff) == 0x64){
              double count[128]={0};
	      
  	      int i_data;
              data_file.read((char*)&i_data, sizeof(int));
              data_file.read((char*)&i_data, sizeof(int));

              data_file.read((char*)&i_data, sizeof(int));
              if(htonl(i_data) != 0x75504943){
                data_file.read((char*)&i_data, sizeof(int));
                for(int i=0; i<2*511; i++)
                  data_file.read((char*)&i_data, sizeof(int));

                data_file.read((char*)&i_data, sizeof(int));

  		// Hit data
                for(;;){
                  data_file.read((char*)&i_data, sizeof(int));
                  if(htonl(i_data) == 0x75504943 || data_file.eof())
                    break;

                  for(int i=0; i<4; i++){
                    data_file.read((char*)&i_data, sizeof(int));
                    i_data = htonl(i_data);

                    for(int strip=0; strip<32; strip++){
                      if((i_data >> strip) & 0x1)
                        count[32*(3-i) + strip] += 1;
                    }
                  }
                }

                for(int strp=0; strp<128; strp++)
                  total[strp] += (double)count[strp]/1024.;
                event_num++;
              }
            }
          }
        }
      }
    }
    data_file.close();

    if(event_num)
      for(int st=0; st<128; st++)
        DAC_image->Fill(st, fi, (double)total[st]/event_num);
  }
  char ofilename[100];
  sprintf(ofilename, "%s/Vth.root",dirname.c_str());

  //  TFile *RootFile = new TFile("Vth.root", "recreate");
  TFile *RootFile = new TFile(ofilename, "recreate");
  DAC_image->Write();
  RootFile->Close();
  cout<<"written in "<<ofilename<<endl;
}
