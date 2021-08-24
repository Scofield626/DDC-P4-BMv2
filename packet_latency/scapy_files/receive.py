#!/usr/bin/env python
import sys
import os
import time
import argparse
import numpy as np

from scapy.all import sniff, get_if_list, Ether, get_if_hwaddr, IP, Raw, TCP, UDP

def get_if():
    iface=None
    for i in get_if_list():
        if "eth0" in i:
            iface=i
            break;
    if not iface:
        print "Cannot find eth0 interface"
        exit(1)
    return iface

def isNotOutgoing(my_mac):
    my_mac = my_mac
    def _isNotOutgoing(pkt):
        return pkt[Ether].src != my_mac

    return _isNotOutgoing

iface = get_if()
totals = {}
global time_list
time_list = []

def handle_pkt(pkt, output_log):
    print("packet arrived")
    print type(pkt)
    ether = pkt.getlayer(Ether)
    print ether.src
    print ether.dst
    if ether.src == ether.dst:
        #output_log.write("{:.4f}\n".format(time.time())) 
        #output_log.flush()
        time_list.append(time.time())
        print(time_list)

def main():
    
    print "sniffing on %s" % iface
    #my_filter = isNotOutgoing(get_if_hwaddr(get_if()))
    output_log = open("recv_record.txt", "a") 
    sniff(iface = iface,
          prn = lambda x: handle_pkt(pkt=x, output_log=output_log), timeout=30)
    output_log.write("{}".format(iface[:-4]) + " {:4f}\n".format(np.mean(time_list)))
    output_log.close()

if __name__ == '__main__':
    main()

