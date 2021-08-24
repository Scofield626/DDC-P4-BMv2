import json
import argparse
import networkx

num_hosts = 250

topo_base = {
  "program": "main.p4",
  "switch": "simple_switch",
  "compiler": "p4c",
  "options": "--target bmv2 --arch v1model --std p4-16",
  "switch_cli": "simple_switch_CLI",
  "exec_scripts": [],
  "cli": True,
  "pcap_dump": False,
  "enable_log": False,
  "topo_module": {
    "file_path": "",
    "module_name": "p4utils.mininetlib.apptopo",
    "object_name": "AppTopoStrategies"
  },
  "controller_module": None,
  "topodb_module": {
    "file_path": "",
    "module_name": "p4utils.utils.topology",
    "object_name": "Topology"
  },
  "mininet_module": {
    "file_path": "",
    "module_name": "p4utils.mininetlib.p4net",
    "object_name": "P4Mininet"
  },
  "topology": {
      "assignment_strategy": "l3"
  }
}

def create_linear_topo(num_switches):
    topo_base["topology"]["links"] = []

    #connect hosts with switches
    for i in range(1, num_switches+1):
        topo_base["topology"]["links"].append(["h{}".format(i), "s{0}".format(i)])

    #connect switches
    for i in range(1, num_switches):
        topo_base["topology"]["links"].append(["s{}".format(i), "s{}".format(i + 1)])

    topo_base["topology"]["hosts"] = {"h{0}".format(i): {} for i in range(1, num_switches + 1)}
    topo_base["topology"]["switches"] = {"s{0}".format(i): {} for i in range(1, num_switches + 1)}

def create_circular_topo(num_switches):

    create_linear_topo(num_switches)
    #add link between  s1 and sN
    topo_base["topology"]["links"].append(["s{}".format(1), "s{}".format(num_switches)])


def create_random_topo(degree=4, num_switches=10):

    topo_base["topology"]["links"] = []
    g = networkx.random_regular_graph(degree, num_switches)
    trials = 0
    while not networkx.is_connected(g):
        g = networkx.random_regular_graph(degree, num_switches)
        trials +=1
        if trials >= 10:
            print ("Could not Create a connected graph")
            return

    # connect hosts with switches
    for i in range(1, num_switches + 1):
        topo_base["topology"]["links"].append(["h{}".format(i), "s{0}".format(i)])

    for edge in g.edges:
        topo_base["topology"]["links"].append(["s{}".format(edge[0]+1), "s{}".format(edge[1] + 1)])

    topo_base["topology"]["hosts"] = {"h{0}".format(i): {} for i in range(1, num_switches + 1)}
    topo_base["topology"]["switches"] = {"s{0}".format(i): {} for i in range(1, num_switches + 1)}

def create_topo_accord(topo):

    topofile = open(topo)
    num_switches = 0
    topo_base["topology"]["links"] = []
    topo_base["topology"]["hosts"] = {}
    for i in range(1, num_hosts+1): # in p4utils/mininetlib/apptopo.py assert host_num < 254 
        topo_base["topology"]["links"].append(["h{}".format(i), "s{0}".format(i)])

    for line in topofile:
        nodes = line.split(' ')
        topo_base["topology"]["links"].append(["s{}".format(int(nodes[0])),"s{}".format(int(nodes[1]))])
        #topo_base["topology"]["hosts"].append("h{0}".format(int(nodes[0])): {}) #add the hosts for 1st switch in each line
        
        if int(nodes[0]) > num_switches:
            num_switches = int(nodes[0])
        if int(nodes[1]) > num_switches:
            num_switches = int(nodes[1])

    topo_base["topology"]["switches"] = {"s{0}".format(i): {} for i in range(1, num_switches + 1)}
    topo_base["topology"]["hosts"] = {"h{0}".format(i): {} for i in range(1, num_switches + 1)}
   
def main():
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_name', type=str, required=False, default="p4app_test.json")
    parser.add_argument("--topo", type=str, default="random")
    parser.add_argument('-n', type=str, required=False, default=10)
    parser.add_argument('-d', type=str, required=False, default=4)
    parser.add_argument('--topo_data', type = str, required=False, default = None)
    args = parser.parse_args()

    if args.topo == "linear":
        create_linear_topo(int(args.n))
    elif args.topo == "circular":
        create_circular_topo(int(args.n))
    elif args.topo == "random":
        create_random_topo(int(args.d), int(args.n))
    elif args.topo == "accord":
        create_topo_accord(args.topo_data)

    json.dump(topo_base, open(args.output_name, "w"), sort_keys=True, indent=2)
