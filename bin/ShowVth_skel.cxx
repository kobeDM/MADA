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

int ShowVth(){
  TString s_infile;
  TCanvas *c1 = new TCanvas("c1", "c1", 800, 600);
  s_infile="RUNID/Vth.root";
  TFile *file_in;
  file_in = new TFile(s_infile);
  //  file_in->ls();
  TH2F *DAC_image = (TH2F*) file_in->Get("DAC_image");
  DAC_image->GetZaxis()->SetRangeUser(0.,1.2);
  DAC_image->SetTitle("Vth scan ( RUNID, IP)");
  DAC_image->Draw("COLZ");
  //TLine *l= new TLine(0,9000,128,9000);
  TLine *l= new TLine(0,VTH,128,VTH);
  l->SetLineColor(2);
  l->SetLineWidth(4);
  l->Draw("same");
  c1->Print("Vthcheck.png");
  return 0;
}
