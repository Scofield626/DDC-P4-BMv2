import json
import networkx
from collections import Counter

topofile = open('./topo/1239.bb')
num = 0
list_1 = []
for line in topofile:
    nodes = line.split(" ")
    #if int(nodes[0])== 12: num+=1
    #if int(nodes[1])== 12: num+=1
    for node in nodes:
        list_1.append(int(node))
quan = Counter(list_1)
max_num = max(quan.values())
print(max_num)
