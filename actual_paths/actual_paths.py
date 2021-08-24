from p4utils.utils.topology import Topology
from p4utils.utils.sswitch_API import SimpleSwitchAPI
import sys

#print sys.getrecursionlimit()
sys.setrecursionlimit(10000)
#print sys.getrecursionlimit()
sys.stdout = open('./AS2914.log', 'wt') 
topo = Topology(db = "topology.db")
controllers = {}
for p4switch in topo.get_p4switches():
    thrift_port = topo.get_thrift_port(p4switch)
    controllers[p4switch] = SimpleSwitchAPI(thrift_port)

def compute_actual_paths(src_seq, dest_seq, actual_paths):
    

    direction = controllers["s{}".format(src_seq)].register_read('link_directions',dest_seq-1)
    linkState = controllers["s{}".format(src_seq)].register_read('linkState',0)
    if linkState == None: linkState = 0
    condition = direction | linkState
    outport = 1
    while condition > 0:
        if (condition&1) == 1:
            outport += 1
            condition = condition >> 1
        else: break    
    intfs = topo.get_interfaces_to_port("s{}".format(src_seq))
    # return a dictionaary interface_name -> port_num
    intf = list(intfs.keys())[list(intfs.values()).index(outport)]
    next_hop = topo.interface_to_node(node = "s{}".format(src_seq), intf = intf)
    next_src_seq = int(next_hop[1:])
    actual_paths.append((src_seq, next_src_seq))
    #print("actual path is %s"%actual_paths)
    if next_src_seq != dest_seq:
        compute_actual_paths(next_src_seq, dest_seq, actual_paths)
    else:
        #with open('./FatTree.log','wt') as f:
        #    print(actual_paths, file=f)
        print actual_paths


if __name__ ==  "__main__":
 
    num_hosts = 250
    for i in range(1,1+num_hosts):
        for j in range(1,1+num_hosts):
            if j!=i: 
                i_j_paths = compute_actual_paths(i,j,actual_paths=[])
                #print("from %s to %s --> %s"%(i,j,i_j_paths))

