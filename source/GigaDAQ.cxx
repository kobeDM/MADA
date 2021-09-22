#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include <signal.h>
#include <time.h>
#include "RBCP.h"
#include "SiTCP.h"

using namespace std;

bool end_flag;

void EndSeq(int){
  end_flag=1;
}

int main(int argc, char *argv[]){
  //  int debug=1;
  if(argc!=2){
    cerr << " USAGE> GigaDAQ [IP address] " << endl;
    exit(1);
  }
  string IPaddr = argv[1];
  end_flag = 0;
  int BoardNo = atoi(IPaddr.substr(IPaddr.rfind('.')+1, 
				   IPaddr.size()-IPaddr.rfind('.')).c_str());
  
  //BoardNo -= 16;

  char filename[100];
  char infofname[100];
  bool file_opened=0;
  unsigned f_index=0;
  SiTCP EtherDAQ(IPaddr);
  ofstream OutData;
  ofstream OutDataf;
  signal(SIGINT, EndSeq);

  while(1){
    if(end_flag)
      break;

    if(!file_opened){
      sprintf(filename, "GBIP_%02d_%04d.raw", BoardNo, f_index);
      sprintf(infofname, "GBIP_%02d_%04d.info", BoardNo, f_index);
      OutData.open(filename, ios::out);
      OutDataf.open(infofname, ios::out);
      f_index++;
      cout<<"opened "<<filename<<endl;
      file_opened=1;
    }
    char c_data[4096];
    int num = EtherDAQ.Read(c_data);
    if(num>0){
      OutData.write(c_data, num);
    }
    if(OutData.tellp() > 0x2000000){
      OutData.close();
      OutDataf.close();
      file_opened=0;
    }
  }

  signal(SIGINT, SIG_DFL);
}
