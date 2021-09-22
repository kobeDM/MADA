#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include "RBCP.h"

using namespace std;

int main(int argc, char *argv[]){
  if(argc!=2){
    cerr << " USAGE> read_CtrlMem [IP address] " << endl;
    exit(1);
  }
  string IPaddr = argv[1];

  RBCP SlowCtrl;
  SlowCtrl.Open(IPaddr);
  SlowCtrl.ReadRBCP();
}
