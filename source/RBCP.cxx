#include "RBCP.h"
#include <unistd.h>
bool RBCP::Open(const string ip)
{
  if (!dev_num)
  {
    param.sin_port = htons(4660);
    param.sin_family = AF_INET;
    param.sin_addr.s_addr = inet_addr(ip.c_str());

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0)
    {
      cerr << " ERROR(RBCP): Can't open socket" << endl;
      return 1;
    }

    dev_num++;
  }

  pack_id = 0;
  command[0] = 0xff;

  return 0;
}

void RBCP::Close()
{
  if (dev_num)
    close(sock);
}

int RBCP::ReadRBCP()
{
  command[1] = 0xc0;
  command[2] = pack_id & 0xff;
  command[3] = 0x91;
  command[4] = 0x00;
  command[5] = 0x00;
  command[6] = 0x00;
  command[7] = 0x00;
  int num = sendto(sock, command, 8, 0,
                   (struct sockaddr *)&param, sizeof(param));
  pack_id++;

  if (num < 0)
  {
    cerr << " ERROR(RBCP): Can't send command" << endl;
    return -1;
  }

  if (CheckReply(8))
  {
    num = recvfrom(sock, reply, 512, 0, NULL, NULL);
    for (int i = 0; i < num - 9; i++)
    {
      if (i % 16 == 0)
        cout << hex << setw(2) << setfill('0') << i << '\t';
      cout << hex << setw(2) << setfill('0')
           << (unsigned)(reply[i + 9] & 0xff) << ' ';
      if (i % 16 == 15)
        cout << endl;
    }
    cout << endl;

    return num;
  }
  else
    cerr << " No Reply " << endl;

  return 0;
}

int RBCP::WriteRBCP(int address, char *cmd, int length)
{
  command[1] = 0x80;
  command[2] = pack_id & 0xff;
  command[3] = length & 0xff;
  command[4] = (address >> 24) & 0xff;
  command[5] = (address >> 16) & 0xff;
  command[6] = (address >> 8) & 0xff;
  command[7] = address & 0xff;
  for (int i = 0; i < length; i++)
    command[8 + i] = cmd[i];

  int num;
  int flag;
  for (int act = 0; act < 10; act++)
  {
    flag = 1;
    num = sendto(sock, command, length + 8, 0,
                 (struct sockaddr *)&param, sizeof(param));
    pack_id++;

    if (num < 0)
    {
      cerr << " ERROR(RBCP): Can't send command" << endl;
      return -1;
    }

    if (CheckReply(length + 8))
    {
      num = recvfrom(sock, reply, 512, 0, NULL, NULL);
      for (int i = 0; i < num; i++)
      {
        if (i != 1)
        {
          if (reply[i] != command[i])
            flag = 0;
        }
        else if ((unsigned)(reply[i] & 0xff) != 0x88)
          flag = 0;
      }
      if (flag)
        break;
      else
        cerr << " ERROR(RBCP): Not match reply" << endl;
    }
    else
      cerr << " No Reply " << endl;
  }

  return num;
}

int RBCP::CheckReply(int length)
{
  int rev;
  for (int i = 0; i < 10; i++)
  {
    fd_set fdset;
    FD_ZERO(&fdset);
    FD_SET(sock, &fdset);

    struct timeval timeout;
    timeout.tv_sec = 1;
    timeout.tv_usec = 0;

    rev = select(sock + 1, &fdset, NULL, NULL, &timeout);
    if (!rev)
      cerr << " Time out... " << endl;
    else
      break;

    command[2] = pack_id & 0xff;
    int num = sendto(sock, command, length, 0,
                     (struct sockaddr *)&param, sizeof(param));
    pack_id++;

    if (num < 0)
    {
      cerr << " ERROR(RBCP): Can't send command" << endl;
      return -1;
    }
  }

  return rev;
}

char RBCP::convDAC(int val, bool cal, bool dovr)
{
  char data = (((val >> 0) & 0x1) << 6) + (((val >> 1) & 0x1) << 5) + (((val >> 2) & 0x1) << 4) + (((val >> 3) & 0x1) << 3) + (((val >> 4) & 0x1) << 2) + (((val >> 5) & 0x1) << 1);

  if (cal)
    data += 0x80;
  if (dovr)
    data += 0x01;

  return data;
}

RBCP::RBCP()
{
  dev_num = 0;
}

RBCP::RBCP(const string ip)
{
  dev_num = 0;
  Open(ip);
}

RBCP::~RBCP()
{
  if (dev_num)
    Close();
}
