from ping3 import ping
import sys
import time

TARGET_IPs = [
    "192.168.100.16",
    "192.168.100.17",
    "192.168.100.19",
    "192.168.100.24",
    "192.168.100.25",
    "192.168.100.27"
]

def exec_ping(ip: str) -> str:
    res = ping(ip, timeout=1)
    if res == False or res == None:
        return f'{ip}\tcouldn\'t connect'
    else:
        return f'{ip}\tconnected in {res*1000:.3f} ms'

def main():
    while True:
        out_str = "\n".join(list(map(exec_ping, TARGET_IPs)))
        sys.stdout.write(f'\n{out_str}\033[6A')
        sys.stdout.flush()
        time.sleep(1)

if __name__ == '__main__':
    main()