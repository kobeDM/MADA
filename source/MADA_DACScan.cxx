#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include "RBCP.h"
#include "SiTCP.h"
#include <unistd.h>
using namespace std;

int main(int argc, char *argv[]){
  if(argc!=3){
    cerr << " USAGE> SetDAC [IP address] [Vth val.] " << endl;
    cerr << "   Vth: give a decimal number from 0 and 16383 " << endl;
    exit(1);
  }
  string IPaddr = argv[1];
  int Vth = atoi(argv[2]) & 0x3fff;
  string outfile_config_name ="DACsurvey_config.out";
  ofstream outfile_config;

  outfile_config.open(outfile_config_name.c_str(),ios::out);
  outfile_config<<"IP: "<<IPaddr<<endl;
  outfile_config<<"Vth: "<<Vth<<endl;
  outfile_config.close();





  RBCP SlowCtrl;
  SiTCP EtherData;
  SlowCtrl.Open(IPaddr);
  EtherData.Open(IPaddr);

  // Set Vth
  char cmd[256];
  cmd[0] = (Vth >> 8) & 0x3f;
  cmd[1] = Vth & 0xff;
  SlowCtrl.WriteRBCP(0x80, cmd, 2);
  //  cout << " Vth value write " << endl;

  cmd[0] = 0x01;
  SlowCtrl.WriteRBCP(0xf0, cmd, 1);
  sleep(1);
  cout << " Vth set at " << Vth << endl;
  
  // DAC survey
  for(int i=0; i<64; i++){
    cout << dec;
    // DAC Set
    for(int ch=0; ch<128; ch++)
      cmd[ch] = SlowCtrl.convDAC(i, 0, 0);
    SlowCtrl.WriteRBCP(0, cmd, 128);

    cmd[0] = 0x02;
    SlowCtrl.WriteRBCP(0xf0, cmd, 1);
    sleep(1);
    
    int data_size=0;
    char c_data[4096];
    while(1){
      //      cout << " refleshing buffer..." << '\r' << flush;

      int num = EtherData.Read(c_data);
      if(num>0)
	data_size += num;

      if(data_size > 0x20000)
	break;
    }

    char filename[100];
    sprintf(filename, "DAC_%02d_%04x.srv", i, Vth);
    ofstream OutData(filename, ios::out);
    
    int e_index=0;
    data_size=0;
    while(1){
      //      cout << hex;
      //      cout << " data reading...   " << data_size << '\r' << flush;
      
      int num = EtherData.Read(c_data);
      if(num>0){
	OutData.write(c_data, num);
	data_size += num;
      }

      if(c_data[num-4]=='u' && c_data[num-3]=='P' &&
	 c_data[num-2]=='I' && c_data[num-1]=='C')
	e_index++;
      cout << " DAC value: " <<dec<< i <<"/64: "<<hex<<"data size=0x"<< data_size << " e_index="<<dec<<e_index<<'\r' << flush;

      //      if(data_size > 0x800000 || e_index > 1e4)
      if(data_size > 0x80000 || e_index > 1e3)
	break;
    }

    cout<<endl<<flush;
    //    cout << "                                                         " << '\r'<< flush;
    OutData.close();
  }
}
