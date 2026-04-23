#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include "RBCP.h"
#include <unistd.h>

using namespace std;

int main(int argc, char *argv[]){
  if(argc!=3){
    cerr << " USAGE> SetLatchUpDetect [IP address] [0/1] " << endl;
    cerr << "   Latch-up detection flag 0...OFF, 1...ON " << endl;
    exit(1);
  }
  string IPaddr = argv[1];
  int val = atoi(argv[2]);
  val = val & 0x1;

  RBCP SlowCtrl;
  SlowCtrl.Open(IPaddr);

  char cmd[256];
  
  if (val == 1){
    cmd[0] = 0x01;
  } else {
    cmd[0] = 0x00;
  }

  SlowCtrl.WriteRBCP(0xf2, cmd, 1);
  sleep(1);

  SlowCtrl.ReadRBCP();
}
