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

bool end_flag;

void EndSeq(int)
{
  end_flag = 1;
}

int main(int argc, char *argv[])
{
  string IP = "192.168.100.16"; // defalut
  string filename_head = "";    // default
  int num = 1000;               // default datasize per file
  int vopt = 0;
  int fopt;
  int filenum_max = 100; // defalt maxfile per directory
  //  int debug=1;
  // option handling
  struct option longopts[] = {
      {"help", no_argument, NULL, 'h'},
      {"num", required_argument, NULL, 'n'},
      {"IP", required_argument, NULL, 'i'},
      {"filename", required_argument, NULL, 'f'},
      {0, 0, 0, 0},
  };

  //  if(argc!=2){
  //  cerr << " USAGE> MADA_iwaki [IP address] " << endl;
  //   exit(1);
  // }

  int opt;
  int longindex;
  int numopt = 0;

  while ((opt = getopt_long(argc, argv, "hn:i:f:", longopts, &longindex)) != -1)
  {
    switch (opt)
    {
    case 'h':
      break;
    case 'n':
      num = (atoi)(optarg);
      break;
    case 'f':
      fopt = 1;
      filename_head = optarg;
      filenum_max = 1;
      break;
    case 'i':
      IP = optarg;
      break;
    default:
      return 1;
    }
  }

  //  string IPaddr = argv[1];
  cout << "IP: " << IP << endl;
  end_flag = 0;
  int BoardNo = atoi(IP.substr(IP.rfind('.') + 1,
                               IP.size() - IP.rfind('.'))
                         .c_str());

  // BoardNo -= 16;

  char filename[100];
  char infofname[100];
  bool file_opened = 0;
  unsigned f_index = 0;
  SiTCP EtherDAQ(IP);
  ofstream OutData;
  ofstream OutDataf;
  signal(SIGINT, EndSeq);

  //  while(1){
  while (f_index < filenum_max)
  {
    if (end_flag)
      break;

    if (!file_opened)
    {
      if (fopt)
      {
        sprintf(filename, "%s.raw", filename_head.c_str());
        sprintf(infofname, "%s.info", filename_head.c_str());
      }
      else
      {
        sprintf(filename, "GBIP_%02d_%04d.raw", BoardNo, f_index);
        sprintf(infofname, "GBIP_%02d_%04d.info", BoardNo, f_index);
      }
      OutData.open(filename, ios::out);
      OutDataf.open(infofname, ios::out);
      f_index++;
      cout << "opened " << filename << endl;
      file_opened = 1;
    }
    char c_data[4096];
    int num = EtherDAQ.Read(c_data);
    if (num > 0)
    {
      OutData.write(c_data, num);
    }
    if (OutData.tellp() > (num * 100000))
    {
      //    if(OutData.tellp() > 0x2000000){
      OutData.close();
      OutDataf.close();
      file_opened = 0;
    }
  }

  signal(SIGINT, SIG_DFL);
}
