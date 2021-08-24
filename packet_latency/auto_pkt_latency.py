import os
import threading
import subprocess
import sys
import time
import random

#semaphore = threading.Semaphore(2) # the maximum number of threads that run simultaneously

def run_command(r, cmd):
    r.stdin.write(cmd)
    r.stdin.flush()
    print("cmd is %s"%cmd)

def format_command(sender, receiver):
    # create the mininet input format commands
    cmds = ["",""]
    dst_ip = "10.{}.{}.2".format(receiver,receiver)
    cmds[0] = " h{} python scapy_files/send.py --dst_ip ".format(sender) + dst_ip + " --rate 4M &\n"
    cmds[1] = " h{} python scapy_files/receive.py \n".format(receiver) # & will put this command into background
    return cmds


p4run_cmd = ['sudo', 'p4run', '--conf', 'json/AS2914.json']
r1 = subprocess.Popen(p4run_cmd, stdin = subprocess.PIPE) 
time.sleep(1000)
print("p4run fini")
controller_cmd = ['python', 'controller.py']
r2 = subprocess.Popen(controller_cmd, stdin = subprocess.PIPE)    
time.sleep(2040)
print("controller fini")

path_file = open('./selected_path_10_AS2914_1.log')

for whole_path in path_file:
    whole_path = whole_path.strip('[')
    whole_path = whole_path.strip(']\n')
    whole_path = whole_path.split(', ')
    i = 0
    path_list = []
    fail_cmds = []
    while i < 20:
        whole_path[i] = whole_path[i].strip('(')
        whole_path[i] = whole_path[i].strip(')')
        whole_path[i+1] = whole_path[i+1].strip('(')
        whole_path[i+1] = whole_path[i+1].strip(')')
        path_list.append(((int(whole_path[i])), int(whole_path[i+1])))
        fail_cmd = 'fail' + ' s{}'.format(int(whole_path[i])) + ' s{}'.format(int(whole_path[i+1])) + '\n'
        fail_cmds.append(fail_cmd)
        i += 2
    hosts = [path_list[0][0]]
    whole_path[-1].strip(')')
    hosts.append(int(whole_path[-1]))
    print("host pairs are %s"%hosts)
    
    host_indexes = random.sample(range(250),9) # generate destination list
    host_indexes.append(hosts[1])
    print("host_indexes are %s"%host_indexes)

    for index in host_indexes:
        cmds = format_command(hosts[0],index)
   
    # 1st time sending traffic to record normal latency
    for index in host_indexes:
        cmds = format_command(hosts[0],index)
        for i in range(2):
            t = threading.Thread(target=run_command, args=(r1,cmds[i],)).start()
        time.sleep(35)
    
    # 2nd time sending traffic to record latency with 2 failures
    j = 0
    while j < 10:
        if j == 2: 
            for index in host_indexes:
                cmds = format_command(hosts[0],index)
                for i in range(2):
                    t = threading.Thread(target=run_command, args=(r1,cmds[i],)).start()
                time.sleep(35)
        r2.stdin.write(fail_cmds[j])            
        time.sleep(120) # TBD according to real time
        j+=1

    # 3rd time sending traffic to record latency with 10 failures
    for index in host_indexes:
        cmds = format_command(hosts[0],index)
        for i in range(2):
            t = threading.Thread(target=run_command, args=(r1,cmds[i],)).start()
        time.sleep(35)
    
    r2.stdin.write('reset\n')
    time.sleep(120)
    


