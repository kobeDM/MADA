#include "TCPclient.h"

TCPclient::TCPclient(const char *server, int port)
{
  struct hostent *s_host;
  s_host = gethostbyname(server);
  addr.sin_port = htons(port);
  addr.sin_family = AF_INET;
  addr.sin_addr = *(struct in_addr *)(s_host->h_addr_list[0]);
  ClntSock = socket(AF_INET, SOCK_STREAM, 0);

  int flag = connect(ClntSock, (struct sockaddr *)&addr, sizeof(addr));
  if (flag)
  {
    syslog(LOG_NOTICE, "cannot connect to %s [%d]", server, port);
    alive_flag = 0;
  }
  else
  {
    syslog(LOG_NOTICE, "connected to %s [%d]", server, port);
    alive_flag = 1;

    int val = 1;
    ioctl(ClntSock, FIONBIO, &val);

    int opt = 1;
    setsockopt(ClntSock, SOL_SOCKET, SO_KEEPALIVE, (void *)&opt, sizeof(opt));
    // opt = 5;
    // setsockopt(ClntSock, IPPROTO_TCP, TCP_USER_TIMEOUT,
    //	       (void*)&opt, sizeof(opt));
  }
}

bool TCPclient::isAlive()
{
  return alive_flag;
}

int TCPclient::SendMessage(void *ptr, int size)
{
  int flag = send(ClntSock, ptr, size, 0);
  return flag;
}

int TCPclient::RecieveMsg(void *ptr, int size)
{
  int flag = recv(ClntSock, ptr, size, 0);
  return flag;
}

void TCPclient::Close()
{
  close(ClntSock);
  alive_flag = 0;
}
