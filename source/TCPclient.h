#ifndef TCPclient_h
#define TCPclient_h 1

#include <arpa/inet.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <string>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <syslog.h>
#include <unistd.h>

using namespace std;

class TCPclient
{
    public:
        TCPclient( const char *, int );
        ~TCPclient( ) {};

        int  SendMessage( void *, int );
        int  RecieveMsg( void *, int );
        bool isAlive( );
        void Close( );

    private:
        int                ClntSock;
        bool               alive_flag;
        struct sockaddr_in addr;
};

#endif
