//// STL
#include <sys/stat.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <algorithm>
#include <time.h>
// ROOT
#include "TROOT.h"
#include "TStyle.h"
#include "TTree.h"
#include "TH1.h"
#include "TH1F.h"
#include "TH2F.h"
#include "TCanvas.h"
#include "TFile.h"
#include "TSystem.h"
#include "TClassTable.h"
#include "TApplication.h"
#include "TGraph.h"
#include "TGraphErrors.h"
#include "TLegend.h"
#include "TPaveText.h"

#include "TText.h"
#include "TBox.h"
#include "TLatex.h"
#include "TString.h"

int ShowVth()
{
  TString s_infile = "Vth.root";
  TFile *file_in = new TFile(s_infile);
  TCanvas *c1 = new TCanvas("c1", "c1", 800, 600);
  TH2F *DAC_image = (TH2F *)file_in->Get("DAC_image");

  // plot result
  DAC_image->GetZaxis()->SetRangeUser(0., 1.2);
  DAC_image->SetTitle("Vth scan ( RUNID, IP)");
  DAC_image->Draw("COLZ");

  TLine *l = new TLine(0, VTH, 128, VTH);

  l->SetLineColor(2);
  l->SetLineWidth(4);
  l->Draw("same");

  c1->Print("Vthcheck.png");

  // save root file
  int ch_num = 128;

  std::ifstream config("./scan_config.out");
  std::string line;

  int vth_low = 0;
  int vth_high = 0;
  int vth_delta = 0;
  while (std::getline(config, line))
  {
    if (line == "")
      continue;
    std::istringstream ss(line);
    std::string key;
    int value;
    ss >> key >> value;
    if (key == "Vth(lower):")
      vth_low = value;
    if (key == "Vth(upper):")
      vth_high = value;
    if (key == "Vth(delta):")
      vth_delta = value;
  }

  std::cout << "Vth(lower): " << vth_low << "\tVth(upper): " << vth_high << "\tVth(delta): " << vth_delta << std::endl;
  int vth_step = (vth_high - vth_low) / vth_delta;
  int ch;
  int center;
  std::vector<float> v_rate;
  std::vector<int> v_vth;
  v_rate.reserve(vth_step);
  v_vth.reserve(vth_step);

  TFile *file = new TFile("Vth_val.root", "RECREATE");
  TTree *tree = new TTree("tree", "");

  tree->Branch("ch", &ch, "ch/I");
  tree->Branch("center", &center, "center/I");
  tree->Branch("rate", &v_rate);
  tree->Branch("vth", &v_vth);

  for (ch = 0; ch < ch_num; ch++)
  {
    int vth = vth_low;
    int center_vth = 0;
    float center_rate = 0;
    for (int step = 0; step < vth_step; step++)
    {
      float rate = DAC_image->GetBinContent(ch + 2, step + 1);
      v_rate.push_back(rate);
      v_vth.push_back(vth);
      if (std::fabs(rate - 0.5) < std::fabs(center_rate - 0.5))
      {
        center_vth = vth;
        center_rate = rate;
      }
      vth += vth_delta;
    }
    center = center_vth;
    tree->Fill();
    v_rate.clear();
    v_vth.clear();
  }

  tree->Write();
  file->Close();

  delete file;

  return 0;
}
