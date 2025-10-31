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

#define CAL 52. // dac/Vth

void DACValueCorrection(const std::string rootfile, const std::string dacfile, const std::string outputFile)
{
    // Read root file
    TFile *file = new TFile(rootfile.c_str(), "READ");
    if (!file)
    {
        std::cout << "Error: Root file " << rootfile << "is not found !!" << std::endl;
        exit(1);
    }

    TTree *tree = (TTree *)file->Get("tree");
    int channel;
    int center;
    tree->SetBranchAddress("ch", &channel);
    tree->SetBranchAddress("center", &center);
    const int nentries = tree->GetEntries();

    std::cout << "Total channel: " << nentries << " ch." << std::endl;
    
    double center_ave = 0;
    for (int i = 0; i < nentries; i++)
    {
        tree->GetEntry(i);
        center_ave += center / CAL / nentries;
        // center_ave += center / nentries;
    }

    double center_diff[nentries];
    for (int i = 0; i < nentries; i++)
    {
        tree->GetEntry(i);
        center_diff[i] = center / CAL - center_ave;
    }

    std::cout << "Average Vth value is " << center_ave * CAL << std::endl;
    // std::cout << "Average Vth value: " << center_ave << std::endl;

    // Read DAC file
    std::ifstream ifs(dacfile);
    if (!ifs)
    {
        std::cout << "Error: DAC file " << dacfile << "is not found !!" << std::endl;
        exit(1);
    }
    std::string line;

    std::ofstream ofs;
    ofs.open(outputFile, std::ios::out);

    int id = 0;
    while (std::getline(ifs, line))
    {
        if (line == "") continue;
        int ch, dac;
        std::istringstream ss(line);
        ss >> ch >> dac;
        ofs << ch << "\t" << std::round(dac - center_diff[id]) << std::endl;
        id++;
    }

    ofs.close();

    return;
}