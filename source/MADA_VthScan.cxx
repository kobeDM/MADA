#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include "RBCP.h"
#include "SiTCP.h"
#include <unistd.h>
using namespace std;

int main(int argc, char *argv[]){
  if(argc!=4 && argc!=5){
    cerr << " USAGE> ScanVth [IP address] [start Vth] [end Vth] [delta-Vth]" 
	 << endl;
    cerr << "   Vth: give a decimal number from 0 and 16383 " << endl;
    cerr << "        this program scan Vth from [start Vth] " << endl;
    cerr << "        to [end Vth] with the pitch of [delta-Vth]" << endl;
    cerr << "        default value of [delta-Vth] is 100 in decimal" << endl;
    exit(1);
  }
  string outfile_config_name ="scan_config.out";
  ofstream outfile_config;
  string IPaddr = argv[1];
  int s_Vth = atoi(argv[2]);
  if(s_Vth>0x3fff)s_Vth=0x3fff;
  int e_Vth = atoi(argv[3]);
  if(e_Vth>0x3fff)e_Vth=0x3fff;
  int delta = 100;
  if(argc>4){
    delta = atoi(argv[4]);
    if(delta>0x3fff)delta=0x3fff;
  }

  outfile_config.open(outfile_config_name.c_str(),ios::out);
  outfile_config<<"IP: "<<IPaddr<<endl;
  outfile_config<<"Vth(lower): "<<s_Vth<<endl;
  outfile_config<<"Vth(upper): "<<e_Vth<<endl;
  outfile_config<<"Vth(delta): "<<delta<<endl;
  outfile_config.close();


  RBCP SlowCtrl;
  SiTCP EtherData;
  SlowCtrl.Open(IPaddr);
  EtherData.Open(IPaddr);

  for(int Vth=s_Vth; Vth<=e_Vth; Vth+=delta){
    if(Vth>0x3fff) break;
    // Set Vth
    char cmd[256];
    cmd[0] = (Vth >> 8) & 0x3f;
    cmd[1] = Vth & 0xff;
    SlowCtrl.WriteRBCP(0x80, cmd, 2);

    cmd[0] = 0x01;
    SlowCtrl.WriteRBCP(0xf0, cmd, 1);
    sleep(1);
    cout << dec;
    //    cout << " Vth : " << Vth << endl;
    cout << " Vth : " << Vth;
    int data_size=0;
    char c_data[4096];
    cout << " refreshing buffer..."  << flush;
    while(1){
      //      cout << "."  << flush;

      int num = EtherData.Read(c_data);
      //cout << num<<" "  << flush;
      if(num>0)
        data_size += num;

      if(data_size > 0x20000)
        break;
    }
    cout << " done" << '\n' << flush;
    char filename[100];
    sprintf(filename, "Vth_%04x.scn", Vth);
    ofstream OutData(filename, ios::out);
    
    int e_index=0;
    data_size=0;
    while(1){
      cout << hex;
      cout << " data reading...   " << data_size << '\r' << flush;

      int num = EtherData.Read(c_data);
      if(num>0){
        OutData.write(c_data, num);
        data_size += num;
      }
      if(c_data[num-4]=='u' && c_data[num-3]=='P' &&
         c_data[num-2]=='I' && c_data[num-1]=='C')
        e_index++;

      //      if(data_size > 0x400000 || e_index > 1e3)
      if(data_size > 0x100000 || e_index > 1e3)
        break;
    }
    cout << "                                            " << '\r' << flush;
    OutData.close();
  }
}
