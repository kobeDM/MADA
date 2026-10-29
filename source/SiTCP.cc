#include "../include/SiTCP.h"
#include <poll.h>
#include <unistd.h>
bool SiTCP::Open( const string ip )
{
    if ( !dev_num ) {
        param.sin_port        = htons( 24 );
        param.sin_family      = AF_INET;
        param.sin_addr.s_addr = inet_addr( ip.c_str( ) );

        sock = socket( AF_INET, SOCK_STREAM, 0 );
        if ( sock < 0 ) {
            cerr << " ERROR(SiTCP): Can't open socket" << endl;
            return 1;
        }
        if ( connect( sock, (struct sockaddr *)&param, sizeof( param ) ) ) {
            cerr << " ERROR(SiTCP): Can't connet" << endl;
            return 1;
        }

        dev_num++;
    }

    return 0;
}

void SiTCP::Close( )
{
    if ( dev_num )
        close( sock );
}

int SiTCP::Read( char *data )
{
    int num = recv( sock, data, 4096, 0 );

    return num;
}

int SiTCP::ReadTimeout( char *data, int timeout_ms )
{
    struct pollfd pfd;
    pfd.fd     = sock;
    pfd.events = POLLIN;
    if ( poll( &pfd, 1, timeout_ms ) <= 0 )
        return -1;

    return recv( sock, data, 4096, 0 );
}

SiTCP::SiTCP( )
{
    dev_num = 0;
}

SiTCP::SiTCP( const string ip )
{
    dev_num = 0;
    Open( ip );
}

SiTCP::~SiTCP( )
{
    if ( dev_num )
        Close( );
}
