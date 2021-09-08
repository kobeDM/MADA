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

//bool end_flag;

//void EndSeq(int){
//  end_flag=1;
//}

int MADA_iwaki(std::string IP,std::string filename_head,int maxnum){
  bool debug =0;
  bool  end_flag = 0;
  int BoardNo = atoi(IP.substr(IP.rfind('.')+1,IP.size()-IP.rfind('.')).c_str()); 
  char filename[100];
  SiTCP EtherDAQ(IP);
  ofstream OutData;
  //ofstream OutDataf;
   //  signal(SIGINT, EndSeq);
  sprintf(filename, "%s.raw",filename_head.c_str());
  //sprintf(infofname, "%s.info", filename_head.c_str());
  OutData.open(filename, ios::out);
  //OutDataf.open(infofname, ios::out);
  cout<<"\tDatafile "<<filename<<""<<std::endl;
  //  cout<<"\tInfofile "<<infofname<<""<<endl;
  char c_data[4096];
  int num;
  while(!end_flag){
    num = EtherDAQ.Read(c_data);
    if(num>0){      
      OutData.write(c_data, num);
      //      cout<<"tellp in "<<filename<<": "<<OutData.tellp()<<endl;
     if(debug)  cout<<filename_head<<": "<<OutData.tellp()<<"/"<<maxnum<<"(Byte)"<<endl;
    }
    if(OutData.tellp() > maxnum){
      if(debug)      cout<<filename_head<<" ending : "<<OutData.tellp()<<"/"<<maxnum<<"(Byte)"<<endl;
      cout<<"\t"<<OutData.tellp()<<" bytes stored in "<<filename<<endl;
      
      //if(OutData.tellp() > 0x2000000){
      OutData.close();
      //      OutDataf.close();
      end_flag=1;
      //      break;
      //file_opened=0;
    }
  }

   //  signal(SIGINT, SIG_DFL);
  return 0;
}
