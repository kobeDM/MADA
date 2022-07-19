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

//int MADA_iwaki(std::string IP,std::string filename_head,int maxnum){
int main(int argc, char* argv[]){
  //int main(std::string IP,std::string filename_head,int maxnum){
  bool debug =0;
  bool  end_flag = 0;
  int numperfile=1000;//default numofevents per file
  //  int BoardNo = atoi(IP.substr(IP.rfind('.')+1,IP.size()-IP.rfind('.')).c_str()); 
  //  char filename[100];
  string filename;
  string IP;
  // SiTCP EtherDAQ(IP);
  ofstream OutData;
  struct option longopts[] = {
      { "help", no_argument, NULL, 'h' },
      { "numperdir", required_argument, NULL, 'n' },
      { "filename", required_argument, NULL, 'f' },
      { "IP", required_argument, NULL, 'i' },
      { 0,        0,                 0,     0  },
  };

  int opt,longindex;
  int hopt=0;
  int numopt=0;
  while ((opt = getopt_long(argc, argv, "hn:f:i:", longopts, &longindex)) != -1) {
    //    printf("%d %s\n", longindex, longopts[longindex].name);
    switch (opt) {
    case 'h':
      hopt = 1;
      numopt++;
      break;

    case 'n':
      numopt+=2;
      numperfile=(atoi)(optarg)<<20;
      break;
    case 'i':
      numopt+=2;
      IP=optarg;
      break;
    case 'f':
      numopt+=2;
      filename=optarg;
      break;
    }
  }
  if(hopt){
    //    cout<<"help message";
    printf("MADA [-h || -help] [-n numperfile] [-f filename [-i IP");
    return 0;
  } 
  SiTCP EtherDAQ(IP);
    //ofstream OutDataf;
   //  signal(SIGINT, EndSeq);
    //  sprintf(filename, "%s.raw",filename_head.c_str());
  //sprintf(infofname, "%s.info", filename_head.c_str());
  OutData.open(filename, ios::out);
  //OutDataf.open(infofname, ios::out);
  cout<<"Datafile "<<filename<<""<<std::endl;
  cout<<"IP:"<<IP<<endl;;

  //  cout<<"\tInfofile "<<infofname<<""<<endl;
  char c_data[4096];
  int num;
  int maxnum=numperfile;
  while(!end_flag){
    num = EtherDAQ.Read(c_data);
    if(num>0){      
      OutData.write(c_data, num);
      //      cout<<"tellp in "<<filename<<": "<<OutData.tellp()<<endl;
    }
    //    cout<<OutData.tellp()<<endl;
    //    cout<< std::ios::dec<<setw(4)<<setprecision(1)<<OutData.tellp()/1e6<<"/"<<maxnum/1e6<<" Mbytes stored\r";
    cout<< fixed<<setw(4)<<setprecision(1)<<OutData.tellp()/1.e6<<"/"<< setw(4)<<setprecision(1)<<maxnum/1.e6<<" Mbytes stored\r";
    if(OutData.tellp() > maxnum){
      //      if(debug)      cout<<filename_head<<" ending : "<<OutData.tellp()<<"/"<<maxnum<<"(Byte)"<<endl;
      cout<<"\t"<<scientific << setprecision(2) <<double(OutData.tellp())<<" bytes stored in "<<filename<<endl;
      
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
