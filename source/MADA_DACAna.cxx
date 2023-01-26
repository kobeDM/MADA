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

using namespace std;

int main(int argc, char *argv[])
{
  if (argc != 3)
  {
    cerr << " USAGE> DAC_Analysis [data dir.] [Vth val.]" << endl;
    cerr << "  Vth: give a decimal number from 0 and 16383 " << endl;
    exit(1);
  }
  string dirname = argv[1];
  int Vth = atoi(argv[2]) & 0x3fff;

  TRint app("app", &argc, argv);
  gStyle->SetOptStat(0);

  string outfile_config_name = "DAC_ana_config.out";
  ofstream outfile_config;

  outfile_config.open(outfile_config_name.c_str(), ios::out);
  outfile_config << dirname << endl;
  outfile_config.close();

  string figtitle = "DAC survey (" + dirname + ")";

  TH2F *DAC_image = new TH2F("DAC_image", figtitle.c_str(),
                             130, -1.5, 128.5, 64, -0.5, 63.5);

  for (int fi = 0; fi < 64; fi++)
  {
    char filename[100];
    sprintf(filename, "%s/DAC_%02d_%04x.srv", dirname.c_str(), fi, Vth);
    cout << filename << '\r' << flush;

    double event_num = 0;
    double total[128] = {0};
    ifstream data_file(filename);
    if (!data_file)
    {
      cerr << " Can't find " << filename << endl;
      exit(1);
    }

    while (data_file)
    {
      char data;
      data_file.read(&data, 1);
      if (data_file.eof())
        break;

      if ((data & 0xff) == 0xeb)
      {
        data_file.read(&data, 1);
        if ((data & 0xff) == 0x90)
        {
          data_file.read(&data, 1);
          if ((data & 0xff) == 0x19)
          {
            data_file.read(&data, 1);
            if ((data & 0xff) == 0x64)
            {
              double count[128] = {0};

              int i_data;
              data_file.read((char *)&i_data, sizeof(int));
              data_file.read((char *)&i_data, sizeof(int));

              data_file.read((char *)&i_data, sizeof(int));
              if (htonl(i_data) != 0x75504943)
              {
                data_file.read((char *)&i_data, sizeof(int));
                for (int i = 0; i < 2 * 511; i++)
                  data_file.read((char *)&i_data, sizeof(int));

                data_file.read((char *)&i_data, sizeof(int));

                // Hit data
                for (;;)
                {
                  data_file.read((char *)&i_data, sizeof(int));
                  if (htonl(i_data) == 0x75504943 || data_file.eof())
                    break;

                  for (int i = 0; i < 4; i++)
                  {
                    data_file.read((char *)&i_data, sizeof(int));
                    i_data = htonl(i_data);

                    for (int strip = 0; strip < 32; strip++)
                    {
                      if ((i_data >> strip) & 0x1)
                        count[32 * (3 - i) + strip] += 1;
                    }
                  }
                }

                for (int strp = 0; strp < 128; strp++)
                  total[strp] += (double)count[strp] / 1024.;
                event_num++;
              }
            }
          }
        }
      }
    }
    data_file.close();

    if (event_num)
      for (int st = 0; st < 128; st++)
      {
        double rate = total[st] / event_num;
        if (rate > 2)
          rate = 0;
        //	DAC_image->Fill(st, fi, (double)total[st]/event_num);
        DAC_image->Fill(st, fi, rate);
      }
  }
  TFile *RootFile = new TFile("DAC.root", "recreate");
  DAC_image->Write();
  RootFile->Close();

  ofstream DacOut("base_correct.dac", ios::out);
  TH1F *proj = new TH1F("proj", "", 64, -0.5, 63.5);
  //  TF1 *erf = new TF1("erf", "[0] * TMath::Erf((x-[1])/[2])+0.5");
  TF1 *erf = new TF1("erf", "[0] * TMath::Erf((x-[1])/[2])+[3]");
  TCanvas *ViewWin = new TCanvas("ViewWin", "", 0, 0, 800, 600);
  ViewWin->SetGridx();
  ViewWin->SetGridy();
  ViewWin->Draw();
  for (int strip = 0; strip < 128; strip++)
  {
    for (int dac = 0; dac < 64; dac++)
      proj->SetBinContent(dac + 1,
                          DAC_image->GetBinContent(strip + 2, dac + 1));

    char histname[50];
    sprintf(histname, "%s/Ch %03d", dirname.c_str(), strip);
    proj->SetTitle(histname);

    // double pol = 0.5 - proj->GetBinContent(1);
    // double avr = proj->GetMean();

    //    erf->SetParameters(pol, avr, 5,0.5);
    if (proj->GetBinContent(4) > 0.5)
      erf->SetParameters(-0.5, 31, 5, 0.5);
    else
      erf->SetParameters(0.5, 31, 5, 0.5);

    //    proj->Fit("erf", "", "", 0, 64);
    proj->Fit("erf", "", "", 4, 60);

    proj->Draw();
    ViewWin->Update();
    int DACval = TMath::FloorNint(proj->GetFunction("erf")->GetParameter(1) + 0.5);
    if (DACval < 0)
      DACval = 0;
    if (DACval > 63)
      DACval = 63;
    DacOut << strip << '\t'
           //	   << TMath::FloorNint(proj->GetFunction("erf")->GetParameter(1) + 0.5)
           << DACval
           << endl;
    sprintf(histname, "%s/Ch_%03d.png", dirname.c_str(), strip);
    ViewWin->Print(histname);
    //    sleep(1);
  }
}
