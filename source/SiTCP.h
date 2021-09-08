#ifndef SiTCP_h
#define SiTCP_h 1

#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include <fstream>
#include <string>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>

using namespace std;

class SiTCP {
 public:
  SiTCP();
  SiTCP(const string);
  ~SiTCP();

  bool   Open(const string);
  void   Close();

  int    Read(char*);

 private:
  struct sockaddr_in    param;
  int                   sock;
  int                   dev_num;
};

#endif
