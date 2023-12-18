#include "SiTCP.h"
#include <unistd.h>
bool SiTCP::Open(const string ip)
{
  if (!dev_num)
  {
    param.sin_port = htons(24);
    param.sin_family = AF_INET;
    param.sin_addr.s_addr = inet_addr(ip.c_str());

    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0)
    {
      cerr << " ERROR(SiTCP): Can't open socket" << endl;
      return 1;
    }
    if (connect(sock, (struct sockaddr *)&param, sizeof(param)))
    {
      cerr << " ERROR(SiTCP): Can't connet" << endl;
      return 1;
    }

    dev_num++;
  }

  return 0;
}

void SiTCP::Close()
{
  if (dev_num)
    close(sock);
}

int SiTCP::Read(char *data)
{
  int num = recv(sock, data, 4096, 0);

  return num;
}

int SiTCP::Read(char *data, int timeout_sec)
{
  // enable non-blocking mode
  int val = 1;
  ioctl(sock, FIONBIO, &val);

  int len = 0;
  time_t start_time = time(NULL);
  while (1)
  {
    if (time(NULL) - start_time > timeout_sec)
    {
      printf("Timeout\n");
      return len;
    }
    // else if (time(NULL) - start_time > 0)
    // {
    //   cout << "waiting... " << time(NULL) - start_time << " seconds elapsed" << endl;
    // }

    len = recv(sock, data, 4096, 0);
    if (len < 0)
    {
      if (errno == EAGAIN)
      {
        usleep(1000000);
      }
      else
      {
        perror("recv");
        break;
      }
    }
    else
    {
      break;
    }
  }
  return len;
}

SiTCP::SiTCP()
{
  dev_num = 0;
}

SiTCP::SiTCP(const string ip)
{
  dev_num = 0;
  Open(ip);
}

SiTCP::~SiTCP()
{
  if (dev_num)
    Close();
}
