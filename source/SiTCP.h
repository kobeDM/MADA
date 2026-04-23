#ifndef SiTCP_h
#define SiTCP_h 1

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>

using namespace std;

class SiTCP
{
    public:
        SiTCP( );
        SiTCP( const string );
        ~SiTCP( );

        bool Open( const string );
        void Close( );

        int Read( char * );

    private:
        struct sockaddr_in param;
        int                sock;
        int                dev_num;
};

#endif
