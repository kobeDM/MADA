#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include "RBCP.h"
#include <unistd.h>

using namespace std;

int main(int argc, char *argv[])
{
  if (argc != 3)
  {
    cerr << " USAGE> SetDAC [IP address] [DAC data file] " << endl;
    exit(1);
  }
  string IPaddr = argv[1];
  string filename = argv[2];

  RBCP SlowCtrl;
  SlowCtrl.Open(IPaddr);

  char cmd[256];
  ifstream DAC_data(filename.c_str());
  if (!DAC_data)
  {
    cerr << " ERROR: file not exist " << endl;
    exit(1);
  }
  for (int i = 0; i < 128; i++)
  {
    int ch, dac;
    DAC_data >> ch >> dac;
    cmd[ch] = SlowCtrl.convDAC(dac, 0, 0);
  }
  SlowCtrl.WriteRBCP(0, cmd, 128);

  cmd[0] = 0x02;
  SlowCtrl.WriteRBCP(0xf0, cmd, 1);
  sleep(1);

  SlowCtrl.ReadRBCP();
}
