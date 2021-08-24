import sys
import os
import subprocess
import time
from p4utils.utils.topology import Topology
from networkx.algorithms import all_pairs_dijkstra

p4run_cmd = ['sudo', 'p4run', '--conf', 'json/AS1239.json']
r1 = subprocess.Popen(p4run_cmd, stdin = subprocess.PIPE) 
#time.sleep(150)
time.sleep(600)
#r1.stdout.flush()
print("r1 fini")
controller_cmd = ['python', 'controller.py']
r2 = subprocess.Popen(controller_cmd, stdin = subprocess.PIPE)
    
#time.sleep(75)
time.sleep(1440)
print("r2 fini")
#r1.stdin.write('pingall\n')
#time.sleep(100)
#topo = Topology(db = 'topology.db')
log_file = open('./selected_path.log')
whole_list = []
f = open('test_record_1239.log','w')
       
for whole_path in log_file:
    whole_path_1 = whole_path.strip('[')
    whole_path_2 = whole_path_1.strip(']\n')
    path_len = len(whole_path_2.split('), '))
    if path_len > 9:
        print("path_len is %d"%path_len)
        paths = whole_path_2.split(', ')
        print("paths are %s"%paths)
        i = 0
        node_path = []
        fail_cmd = ''
        while i < 20:
            paths[i] = paths[i].strip('(')
            paths[i] = paths[i].strip(')')
            paths[i+1] = paths[i+1].strip('(')
            paths[i+1] = paths[i+1].strip(')')
            node_path.append(((int(paths[i])),int(paths[i+1])))
            fail_cmd = 'fail' + ' s{}'.format(int(paths[i])) + ' s{}'.format(int(paths[i+1])) + '\n'
            r2.stdin.write(fail_cmd)
            #time.sleep(1.5)
            time.sleep(105)
            i+=2
        time.sleep(10)
        print(node_path)
        hosts = [node_path[0][0]]
        paths[-1].strip(')')
        hosts.append(int(paths[-1]))
        print(hosts)
        failures = []
        topo = Topology(db = 'topology.db')
        graph = topo.network_graph
        for k in node_path:
            failures.append(('s{}'.format(k[0]), 's{}'.format(k[1])))
        for failure in failures:
            graph.remove_edge(*failure)
        dijkstra = dict(all_pairs_dijkstra(graph, weight = 'weight'))
        distances = {node: data[0] for node, data in dijkstra.items()}
        ps_list = []
        if distances['h{}'.format(hosts[0])].has_key('h{}'.format(hosts[1])):
            distance = distances['h{}'.format(hosts[0])]['h{}'.format(hosts[1])]
            regis_cmd = ['simple_switch_CLI', '--thrift-port', '{}'.format(9089+hosts[1])]     
            print regis_cmd
            r3 = subprocess.Popen(regis_cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE)
            for j in range(16):
                ping_cmd = 'h{}'.format(hosts[0])+' ping -c 1 '+'h{}'.format(hosts[1]) + '\n'
                #ping_cmd = 'pingall\n'
                print ping_cmd
                r1.stdin.write(ping_cmd)
                time.sleep(1.5)
                read_cmd = 'register_read MyEgress.hops_number {} \n'.format(hosts[0]-1)       
                print read_cmd
                r3.stdin.write(read_cmd) 
        
            #print r3.communicate()[0]
            result = r3.communicate()[0].split('\n')
            for seq in range(3, 18):
                print('distance is %d'%distance)
                actual_len = int(result[seq].split(' ')[-1])
                print('actual_len is %d'%actual_len)
                ps_list.append(float(actual_len+1)/float(distance))
        else:
            ps_list = [0]
        
        print>>f, ps_list
        whole_list.append(ps_list)
        r2.stdin.write('reset\n')
        time.sleep(105)
    print whole_list
print(whole_list)

