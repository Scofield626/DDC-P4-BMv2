#!/usr/bin/env python
import sys
import socket
import random
from subprocess import Popen, PIPE
import re
import math
import time
import argparse
import numpy as np

# max mtu
MTU = 1500
# min udp packet size
minSizeUDP = 42
maxUDPSize = 1400
DEFAULT_BATCH_SIZE = 1

from scapy.all import sendp, get_if_list, get_if_hwaddr
from scapy.all import Ether, IP, UDP, TCP

def setSizeToInt(size):
    """" Converts the sizes string notation to the corresponding integer
    (in bytes).  Input size can be given with the following
    magnitudes: B, K, M and G.
    """
    if isinstance(size, int):
        return size
    elif isinstance(size, float):
        return int(size)
    try:
        conversions = {'B': 1, 'K': 1e3, 'M': 1e6, 'G': 1e9}
        digits_list = list(range(48, 58)) + [ord(".")]
        magnitude = chr(
            sum([ord(x) if (ord(x) not in digits_list) else 0 for x in size]))
        digit = float(size[0:(size.index(magnitude))])
        magnitude = conversions[magnitude]
        return int(magnitude*digit)
    except:
        print("Conversion Fail")
        return 0

def get_if():
    ifs=get_if_list()
    iface=None # "h1-eth0"
    for i in get_if_list():
        if "eth0" in i:
            iface=i
            break;
    if not iface:
        print "Cannot find eth0 interface"
        exit(1)
    return iface

def get_dst_mac(ip):

    try:
        pid = Popen(["arp", "-n", ip], stdout=PIPE)
        s = pid.communicate()[0]
        mac = re.search(r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", s).groups()[0]
        return mac
    except:
        return None

def send_traffic(dst_ip, tos=0, rate='4M', duration=25, startTime=5,
                packet_size=maxUDPSize, batch_size=DEFAULT_BATCH_SIZE, out_file="send.txt", **kwargs):

    packet_size = int(packet_size)
    tos = int(tos)
    if packet_size > maxUDPSize:
        packet_size = maxUDPSize

    rate = int(setSizeToInt(rate)/8)
    totalTime = float(duration)
    print totalTime
    dst_addr = socket.gethostbyname(dst_ip)
    total_pkts = 0
    random_port = random.randint(1024,65000)
    iface = get_if()
    #ether_dst = get_dst_mac(dst_addr)
    host_seq = int(dst_addr.split(".")[1])
    host_name = "h{}".format(host_seq)
    if host_seq <= 9: 
        host_seq = "0"+ str(host_seq)
    else:
        host_seq = str(hex(host_seq))[2:]
    print host_seq
    ether_dst = "00:00:0a:{}:{}:02".format(host_seq, host_seq)
    print ether_dst

    p = Ether(dst=ether_dst, src=get_if_hwaddr(iface)) / IP(dst=dst_addr)
    p = p / UDP(dport=random_port)
    print dst_addr
    output_log = open(out_file, "a")
    time_list = []
    try:
        startTime = time.time()
        while (time.time() - startTime < totalTime):

            packets_to_send = rate/packet_size
            times = math.ceil((float(rate) / (packet_size))/batch_size)
            time_step = 1/times
            start = time.time()
            i = 0
            packets_sent = 0
            # batches of 1 sec
            while packets_sent < packets_to_send:
                for _ in range(batch_size):
                    sendp(p, iface = iface)
                    time_list.append(time.time())
                    #output_log.write("{:.4f}\n".format(time.time()))
                    #output_log.flush()
                    # sequence_numbers.append(seq)
                    packets_sent += 1

                i += 1
                next_send_time = start + (i * time_step)
                time.sleep(max(0, next_send_time - time.time()))
            time.sleep(max(0, 1-(time.time()-start)))

    finally:
        #output_log.close()
        output_log.write(host_name + " {:4f}\n".format(np.mean(time_list)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dst_ip', type=str, default="10.1.1.2")    
    parser.add_argument('--rate', type=str, default="4M")
    #parser.add_argument('--output', type=str, default="send.txt")
    args = parser.parse_args()

    send_traffic(dst_ip=args.dst_ip, rate=args.rate, out_file="send_record.txt")
