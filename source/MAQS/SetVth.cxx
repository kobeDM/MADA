#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include "RBCP.h"
#include <unistd.h>
using namespace std;

int main(int argc, char *argv[]){
  if(argc!=3){
    cerr << " USAGE> SetVth [IP address] [Vth val.] " << endl;
    cerr << "   Vth: give a decimal number from 0 and 16383 " << endl;
    exit(1);
  }
  string IPaddr = argv[1];
  int val = atoi(argv[2]);
  val = val & 0x3fff;

  RBCP SlowCtrl;
  cout<<"IP:"<<IPaddr<<endl;
  cout<<"Vth:"<<val<<endl;
  
  SlowCtrl.Open(IPaddr);
  //sleep(5);
  char cmd[256];
  cmd[0] = (val >> 8) & 0x3f;
  cmd[1] = val & 0xff;
  SlowCtrl.WriteRBCP(0x80, cmd, 2);
  //sleep(5);

  cmd[0] = 0x01;
  SlowCtrl.WriteRBCP(0xf0, cmd, 1);
  //sleep(5);

  //SlowCtrl.ReadRBCP();
}
