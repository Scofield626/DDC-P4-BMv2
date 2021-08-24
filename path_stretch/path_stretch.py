# -*- coding:utf-8 -*-

import os
import subprocess
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

num_switches = 361
num_hosts = 249
#num_switches = 10
#num_hosts = 10
thrift_port_1 = 9090
thrift_port_2 = thrift_port_1 + num_hosts


# ------------------------------------------------------------------------------
# Acquire the practical distances of packets transmitting between hosts
# ------------------------------------------------------------------------------

whole_list = []
for i in range(thrift_port_1, thrift_port_2):
    start = time.time()
    list_for_each_switch = []
    command = ['simple_switch_CLI', '--thrift-port', '{}'.format(i)]  
    r = subprocess.Popen(command, stdin = subprocess.PIPE, stdout = subprocess.PIPE)
    for j in range(num_hosts):
        #r = subprocess.Popen(command, stdin = subprocess.PIPE, stdout = subprocess.PIPE)
        command_2 = 'register_read MyEgress.hops_number {} \n'.format(j)
        #r1 = r.communicate(input = command_2)[0][-15]
        r.stdin.write(command_2)
        #print(r1)
        #list_for_each_switch.append(int(r1))
        
    result = r.communicate()[0].split("\n")
    #print(result)
    #seq = 0
    for k in range(3, 3+num_hosts):
        # register only recorded the hops which lacks 1, so need to compensate here
        if (int(result[k].split(" ")[-1]))==0:
            list_for_each_switch.append(0)
        else:
            list_for_each_switch.append(int(result[k].split(" ")[-1])+1)
        #seq+=1
    print list_for_each_switch
    end = time.time()
    #print("takes %.2f for this switch"%(end-start))
    whole_list.append(list_for_each_switch)

#print(whole_list) # the practical distances
#_list = []
#for i in range(len(whole_list)):
#    for j in range(len(whole_list[i])):
#        if whole_list[i][j] == 0: 
#            _list.append((i,j))
#print(_list)
# -----------------------------------------------------------------------------
# Now we compute the shortest paths
# -----------------------------------------------------------------------------
from p4utils.utils.topology import Topology
from networkx.algorithms import all_pairs_dijkstra

topo = Topology(db = "topology.db")
graph = topo.network_graph

#failure_file = open('./link_failure_tests/FatTree/5.txt')
failure_file = open('./link_failure_tests/AS1239/3.txt')
failures = []
for line in failure_file:
    nodes = line.split(" ")
    failures.append((unicode(nodes[0]),unicode(nodes[1].replace("\n", ""))))

#for failure in failures:
#    graph.remove_edge(*failure)

dijkstra = dict(all_pairs_dijkstra(graph, weight = 'weight'))
distances = {node: data[0] for node, data in dijkstra.items()}


paths = {node: data[1] for node, data in dijkstra.items()}
for i,j in paths.items():
    if i[0]=="h":
        print("dest is %s"%i)
        for p,q in j.items():
            if p[0]=="h":
                print("scr is %s, the path is %s"%(p,q))
#print distances

hosts_dict = {}
hosts_list = []
for key in distances.keys():
    if key[0]=="h":
        in_dict = {}
        for in_key in distances[key].keys():
            if in_key[0]=="h":
                in_dict[int(in_key[1:])]=distances[key][in_key]
        hosts_dict[int(key[1:])]=in_dict

for i, j in hosts_dict.items():
    hosts_list.append(j.values())

#print hosts_list # The shortest distances


# -----------------------------------------------------------------------------
# Now we calculate Path Stretch (practical/shortest)
# -----------------------------------------------------------------------------

path_stretch = []

def get_median(a):
    a.sort()
    half = len(a)//2
    return (a[half]+a[~half])/2

for i in range(num_hosts):
    a = whole_list[i]
    b = hosts_list[i]
    #path_stretch.append([c/d for c,d in zip(a,b) if d])
    inner_result = []
    for c,d in zip(a,b):
        if c == 0 or d == 0: 
            inner_result.append("1.00")
        else: 
            inner_result.append(format(float(c)/float(d),".2f"))
    path_stretch.append(inner_result)

#print(path_stretch)
#f = open('./log_txt/log_3.txt','w')
#print >> f, path_stretch
#f.close()

list_max = []
list_median = []
for p in path_stretch:
    list_max.append(max([float(q) for q in p]))
    list_median.append(get_median([float(q) for q in p]))

print(list_max)
print(max(list_max))
print(np.mean(list_median))
x_scale = range(num_hosts)
plt.plot(x_scale,list_max, label = "max")
plt.plot(x_scale,list_median, label = "median")

#plt.xlabel('')
plt.ylabel('Path Stretch')
plt.ylim((0,15))
my_y_ticks = np.arange(0,15,1)
plt.yticks(my_y_ticks)
plt.grid()

#plt.savefig("./pathStretch/update_cp/failed10_RF_v1.png")


