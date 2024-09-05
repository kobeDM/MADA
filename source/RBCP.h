#ifndef RBCP_h
#define RBCP_h 1

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

class RBCP
{
public:
  RBCP();
  RBCP(const string);
  ~RBCP();

  bool Open(const string);
  void Close();
  int ReadRBCP();
  int WriteRBCP(int, char *, int);

  char convDAC(int, bool, bool);
  int CheckReply(int);

private:
  struct sockaddr_in param;
  int sock;
  int dev_num;
  unsigned pack_id;
  char command[512];
  char reply[512];
};

#endif
