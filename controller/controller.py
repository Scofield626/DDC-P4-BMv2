import os

from p4utils.utils.topology import Topology
from p4utils.utils.sswitch_API import SimpleSwitchAPI
from cli import CLI
from networkx.algorithms import all_pairs_dijkstra
from collections import defaultdict

class DDC_Controller(object):

	def __init__(self):

		if not os.path.exists("topology.db"):
			print "Could not find topo object!\n"
			raise Exception

		self.topo = Topology(db = "topology.db")
		self.controllers = {}
		self.connect_to_switches()
		self.reset_states()
		self.install_border_check()
		self.install_add_ddc_headers()
		self.install_dest_seq()
		self.install_ipv4_lpm()
                self.init_link_num()
		self.install_choose_outlink()
		self.init_link_direction()
                self.install_edge_priorities()

	def connect_to_switches(self):
		# Connect to all switches in the topology
		for p4switch in self.topo.get_p4switches():
			thrift_port = self.topo.get_thrift_port(p4switch)
			self.controllers[p4switch] = SimpleSwitchAPI(thrift_port)


	def reset_states(self):
		# Resets registers, tables, etc
		for control in self.controllers.values():
			control.reset_state()

        def get_host_net(self,host):
                gateway = self.topo.get_host_gateway_name(host)
                return self.topo[host][gateway]['ip']


	def install_border_check(self):

		for switch, control in self.controllers.items():
			if self.topo.get_hosts_connected_to(switch):
				for host in self.topo.get_hosts_connected_to(switch):
					sw_port = self.topo.node_to_node_port_num(switch,host)
					control.table_add('check_is_ingress_border','set_is_ingress_border', [str(sw_port)])
					control.table_add('check_is_egress_border', 'set_is_egress_border',  [str(sw_port)])


	def install_add_ddc_headers(self):

		host_lists = self.topo.get_hosts()

		for switch, control in self.controllers.items():
			connected_host_lists = self.topo.get_hosts_connected_to(switch)
			not_connected_host_lists = [i for i in host_lists
										if i not in connected_host_lists]
			for not_connected_host in not_connected_host_lists:
				subnet = self.get_host_net(not_connected_host)
				control.table_add('add_ddc_header','do_add_ddc_header',[subnet])


	def install_dest_seq(self):
                i=0
		hosts_list = []
                hosts_list_2 = []
                for j in range(1,len(self.topo.get_hosts())+1):
                    #subnet = self.get_host_net(self.topo.get_hosts()[unicode("h{}".format(j))])
                    #host_value = self.topo.get_hosts()["h{}".format(j)]
                    subnet = self.get_host_net("h{}".format(j))
                    print(subnet)
                    hosts_list_2.append("h{}".format(j))
		    hosts_list.append(subnet)
		    for switch, control in self.controllers.items():
			control.table_add('get_dest_seq','do_get_dest_seq',[subnet],[str(j-1)])
			control.table_add('get_src_seq','do_get_src_seq',[subnet],[str(j-1)])
				#print("i == %d"%i)

		# exclude some links for border switch:
		# At the border switch, when packets go to the destination that is not the connected host to this switch,
		# this link (which will not access the ddc stuff) will be recorded as non_ddc_links for all non_directly connected destinations on the controller of this switch
		# Thus, these non_ddc_links can be used in main.p4 that these non_ddc_links' link_direction will always be IN when reverse all the IN links to OUT. So that these
		# links wouldn't be choosed as OUT links in ddc algo.
                
		for host in self.topo.get_hosts():
			for switch, control in self.controllers.items():
				if self.topo.are_neighbors(switch, host):
					sw_port = self.topo.node_to_node_port_num(switch,host)
					for j in self.topo.get_hosts():
						 if j not in self.topo.get_hosts_connected_to(switch):
				 			 subnet = self.get_host_net(j)
							 index = hosts_list.index(subnet)
							 pre_value = self.controllers[switch].register_read('non_ddc_links',index)
							 self.controllers[switch].register_write('non_ddc_links', index, pre_value + pow(2,sw_port-1))
						 	 print("the non_ddc_links of %s for destination - %s is %s"%(switch,j,self.controllers[switch].register_read('non_ddc_links',index)))


	def install_ipv4_lpm(self):
                graph = self.topo.network_graph
                dijkstra = dict(all_pairs_dijkstra(graph, weight = 'weight'))
                distances = {node: data[0] for node, data in dijkstra.items()}
		for switch, control in self.controllers.items():
			for sw_dst in self.topo.get_p4switches():

				if switch == sw_dst:
					for host in self.topo.get_hosts_connected_to(switch):
						sw_port = self.topo.node_to_node_port_num(switch,host)
						host_ip = self.topo.get_host_ip(host) + '/32'
						host_mac = self.topo.get_host_mac(host)
						control.table_add('ipv4_lpm','ipv4_forward',[str(host_ip)],
											[str(host_mac), str(sw_port)])
				else:
					if self.topo.get_hosts_connected_to(sw_dst):
                                            if distances[switch].has_key(sw_dst):
                                                paths = self.topo.get_shortest_paths_between_nodes(switch, sw_dst)
						for host in self.topo.get_hosts_connected_to(sw_dst):
							next_hop = paths[0][1]

							host_ip = self.topo.get_host_ip(host) + "/24"
							sw_port = self.topo.node_to_node_port_num(switch, next_hop)
							dst_sw_mac = self.topo.node_to_node_mac(next_hop, switch)
							control.table_add("ipv4_lpm", "ipv4_forward", [str(host_ip)],
											[str(dst_sw_mac), str(sw_port)])

	def init_link_num(self):

		for switch, control in self.controllers.items():
			link_num = len(self.topo.get_interfaces_to_node(switch))
			control.register_write('linkNum', 0, link_num)


	def install_choose_outlink(self):
		
		for switch, control in self.controllers.items():
		    priority = 1
                    port_border = 1
                    if self.topo.get_hosts_connected_to(switch):
                        for host in self.topo.get_hosts_connected_to(switch):
	    		    port = self.topo.node_to_node_port_num(switch, host)
    			    mask = '0&&&'+str(pow(2,port-1))
                            action_para = str(port)
		    	    control.table_add('choose_outlink','do_choose_outlink',[mask, mask],[action_para],prio=priority)
	    		priority += 1
                        port_border += 1	

                    linkNum = control.register_read('linkNum',0)
                    for port_to_switch in range(port_border,1+linkNum):
                        mask = '0&&&'+ str(pow(2,port_to_switch-1))
                        action_para = str(port_to_switch)
                     	control.table_add('choose_outlink','do_choose_outlink',[mask, mask],[action_para],prio=priority)
	    		    

	# Ensure init a valid DAG, two nodes on each link have agreed with each other
	def init_link_direction(self):       

		graph = self.topo.network_graph
		dijkstra = dict(all_pairs_dijkstra(graph, weight = 'weight'))
		distances = {node: data[0] for node, data in dijkstra.items()}
		paths = {node: data[1] for node, data in dijkstra.items()}

		switch_dict = {}
		switch_dist_list = []
		for key in distances.keys():
			if key[0]=="h":
				in_dict = {}
				for in_key in distances[key].keys():
					if in_key[0]=="s":
						in_dict[int(in_key[1:])]=distances[key][in_key]
				switch_dict[int(key[1:])]=in_dict

		for i, j in switch_dict.items():
			switch_dist_list.append(j.values())

		dest_num = len(self.topo.get_hosts())

		sorted_list = []
		for i in switch_dist_list:
			sorted_dict = defaultdict(list)
			for j in range(len(i)):
				sorted_dict[i[j]].append(j+1)
			sorted_list.append(sorted_dict)

		list_whole = []
		for k in sorted_list:
			list_1 = []
			for o in range(1,len(k)+1):
				list_1.append(k[o])
			list_whole.append(list_1) # return [[[1],[2,3],[4,5,6,7],[8,9,10]],[...]] sorted by dist

		print(list_whole)
		index_dst = 0
		for switch_dist_per_host in list_whole:
			seq_num = 0
			for sorted_dist in switch_dist_per_host:
				for same_dist_switch_seq in sorted_dist:
					# All Edges Outward
					curr_switch = "s{}".format(same_dist_switch_seq)
					if seq_num != 0 and same_dist_switch_seq <= len(self.topo.get_hosts()): # exclude the non-ddc-links for border switch 
						self.controllers[curr_switch].register_write('link_directions', index_dst, 1)
					else:
						self.controllers[curr_switch].register_write('link_directions', index_dst, 0)
					for connected_switch in self.topo.get_switches_connected_to(curr_switch):
				print(connected_switch) 
						pre_direction = self.controllers[connected_switch].register_read('link_directions',index_dst)
						print("pre_dir is %d"%pre_direction)
						connected_port = self.topo.node_to_node_port_num(connected_switch, curr_switch)
						self.controllers[connected_switch].register_write('link_directions', index_dst, pre_direction + pow(2,connected_port-1))
						print("wrote the link_direction of %s for dest-%d ---- %d"%(connected_switch, index_dst, pre_direction+pow(2,connected_port-1)))
				seq_num += 1 
			index_dst += 1

		#for i in range(dest_num):
		#    for switch,control in self.controllers.items():
		#        link_direction = control.register_read('link_directions',i)
		#        print("link_direction of %s for dest - %d is %s"%(switch, i, link_direction))
                
	def install_edge_priorities(self):
		graph = self.topo.network_graph
		dijkstra = dict(all_pairs_dijkstra(graph, weight = 'weight'))
		distances = {node: data[0] for node, data in dijkstra.items()}
		for host in self.topo.get_hosts():
			dest_seq = int(host[1:])-1
			for switch in self.topo.get_switches():
				if distances[switch].has_key(host):
				all_paths = self.topo.get_shortest_paths_between_nodes(switch, host)                     
				# all paths is a [[]] which includes the path in the order of length
				print all_paths
				seq = 0
				port_list = []
				for path in all_paths:
					port = self.topo.node_to_node_port_num(switch, path[1])
					if port not in port_list:
						self.controllers[switch].register_write('edge_priorities_{}'.format(seq), dest_seq, port)
						print("%s write edge prios %d for %s with %d"%(switch, seq, host, port))
						port_list.append(port)
						seq += 1                                                                            
						if seq == 5: break

if __name__ == "__main__":
	controller = DDC_Controller()
	CLI(controller)
