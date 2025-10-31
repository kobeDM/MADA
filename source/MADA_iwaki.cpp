#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include <signal.h>
#include <time.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include "RBCP.h"
#include "SiTCP.h"

using namespace std;

int main(int argc, char *argv[])
{
  bool debug = 0;
  bool end_flag = 0;
  double numperfile = 1.0;

  string filename;
  string IP;

  ofstream OutData;
  struct option longopts[] = {
      {"help", no_argument, NULL, 'h'},
      {"numperdir", required_argument, NULL, 'n'},
      {"filename", required_argument, NULL, 'f'},
      {"IP", required_argument, NULL, 'i'},
      {0, 0, 0, 0},
  };

  int opt, longindex;
  int hopt = 0;
  int numopt = 0;
  while ((opt = getopt_long(argc, argv, "hn:f:i:", longopts, &longindex)) != -1)
  {
    switch (opt)
    {
    case 'h':
      hopt = 1;
      numopt++;
      break;

    case 'n':
      numopt += 2;
      numperfile = (atoi)(optarg) << 20;
      break;
    case 'i':
      numopt += 2;
      IP = optarg;
      break;
    case 'f':
      numopt += 2;
      filename = optarg;
      break;
    }
  }
  if (hopt)
  {
    printf("MADA [-h || -help] [-n numperfile] [-f filename [-i IP");
    return 0;
  }
  SiTCP EtherDAQ(IP);
  OutData.open(filename, ios::out);
  cout << "Datafile " << filename << "" << std::endl;
  cout << "IP:" << IP << endl;

  char c_data[4096];
  int num;
  int maxnum = numperfile;
  while (!end_flag)
  {
    num = EtherDAQ.Read(c_data);
    if (num > 0)
    {
      OutData.write(c_data, num);
    }

    cout << fixed << setw(4) << setprecision(1) << OutData.tellp() / 1.e6 << "/" << setw(4) << setprecision(1) << maxnum / 1.e6 << " Mbytes stored\r";
    if (OutData.tellp() > maxnum)
    {
      cout << "\t" << scientific << setprecision(2) << double(OutData.tellp()) << " bytes stored in " << filename << endl;

      OutData.close();
      end_flag = 1;
    }
  }

  return 0;
}
