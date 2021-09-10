# [Re] Ensuring Connectivity via Data Plane Mechanisms
[![paper](https://img.shields.io/badge/_-Paper-blue?logo=adobeacrobatreader)](https://doi.org/10.3929/ethz-b-000504320)&nbsp;&nbsp;
> J. Liu, A. Panda, A. Singla, B. Godfrey, M. Schapira, and S. Shenker. "Ensuring connectivity via data plane mechanisms." In:10th USENIX Symposium on Networked Systems Design and Implementation (NSDI 13).2013, pp. 113–126.

This is a replication work of above presented paper, which mainly proposed *Data-Driven Connectivity* (**DDC**) to ensure routing connectivity via data plane mechanisms. 
Nowadays, against the backdrop of the development of [P4](https://p4.org), one can enable the programmabilitiy of network devices to perform simple but extremely fastpacket processing directly in the data plane. 
In this reproduction, we apply DDC upon a software switch, [BMv2 target](https://github.com/p4lang/behavioral-model), using [P4_16](https://p4.org/p4-spec/docs/P4-16-v1.2.2.html). 
We evaluate our implementation against several benchmarks from the original paper, i.e., path stretch and packet latency. 
This README is organised as follows.
 - Repository Structure
 - Quick Guide

## Repository Structure
 - `src/` - DDC in P4_16
 - `controller/` - control plane in Python
 - `topo/` - topology data (AS1239, AS2914, FatTree, etc.)
    - `topology_generate.py` - generate configure file (in `json/`) for compiling p4 program based on the topology data
 - `json/` - configuration file which describes the topology we want to create with the help of mininet and p4-utils package
 - `actual_paths/`
    - `*.log` - records the actual (initial) paths that the packet takes between each two nodes. E.g., `[(1, 17), (17, 2)]` means that the packet sent from h1 to h2 will takes h1-s1-s17-s2-h2.
    - `actual_paths.py` - the simulation in the control plane to compute the paths that packet actually takes
 - `path_stretch/` - the evalution via path stretch (i.e., the ratio between the length of the path a packet takes throughthe network, and the shortest path between the packet’s source and destination in thecurrent network state) 
 - `packet_latency/` - the evaluation via packet latency (the comparison of time that before and after link failures) 
 - `acticle/` - the replication article uses the [ReScience C](https://rescience.github.io/) journal template. Instructions to reproduce the article are provided in the subfolder `README`.

## Quick Guide
### Environmental Setup
#### 1. VM setting
In order to be able to compile P4 code, run it in a software switch (bmv2) and create virtual topologies with hosts, several dependencies and open source tools need to be installed first. If you do not have a P4 VM yet, please follow the [instructions](https://github.com/nsg-ethz/p4-learning/blob/master/vm/README.md) given by Networked System Group, ETHz to set up the VM.

#### 2. Installing P4-utils

[P4 utils](https://github.com/nsg-ethz/p4-utils) is an extension to Mininet to support P4 devices.
It was strongly inspired by the original [p4app](https://github.com/p4lang/p4app) from the [p4lang](https://github.com/p4lang) repository.
See the [P4-utils](https://github.com/nsg-ethz/p4-utils) repository for more information.

If you build the VM with the above instructions, you will have `p4-utils` already installed, however if you already have the required software and use your own machine/VM you can manally install it:

```bash
git clone https://github.com/nsg-ethz/p4-utils.git
cd p4-utils
sudo ./install.sh
```

To update you just simply:

```bash
cd /home/p4/p4-tools/p4-utils
git pull
```

### Executing DDC
1. Compile the P4 program and start on the topology: 
   
   ```bash
   sudo p4run --conf json/<conf file>
   ``` 
   
   This will call a python script that parses the configuration file, creates a virtual network of hosts and p4 switches using mininet, compile the p4 program and load it in the switch. After running p4run you will get the mininet CLI prompt. For simple tests, please choose `10-switches.json` since other topologies take much longer to initialize.
2. Start the controller in another terminal window: 

   ```bash
   python controller/controller.py
   ```  

3. Testing connectivity: 
   
   ```bash
   mininet> h1 ping h2
   ``` 
   
   ```bash
   mininet> pingall
   ```

4. Failing links in the controller:
   
   ```bash
   fail s1 s2
   ```
   
   ```bash
   reset
   ```
   
### Evalution
#### 1. Path Stretch
Path stretch is defined as the ratio between the length of the path a packet takes throughthe network, and the shortest path between the packet’s source and destination in thecurrent network state.

For instance, after running `pingall`, to know the actual path length of the packet from h1 to h2. 
1. Start a new terminal  (the thrift port for h1 is 9090, for h2 is 9091, etc.) : 
  
   ```bash
   simple_switch_CLI ----thrift-port 9091
   ```
    
2. The hops information for h1 is stored in the first element of register `hops_number`, thus input:
  
    ```bash
    register_read MyEgress.hops_number 0
    ```


To know the logic of compute path stretch (i.e., obtain the actual path from above steps, using dijkstra's algorithm to compute shortest path), please refer to 'path_stretch/path_stretch.py'. The automation test (invoking subprocess to automate tests for large AS topo) is realized in `path_stretch/auto_test_ps.py`. 

#### 2. Packet Latency
In the mininet CLI, 
1. Send traffic from h1 to h2 (ip - 10.2.2.2): 
   
   ```bash
   h1 python packet_latency/scapy_files/send.py --dst_ip 10.2.2.2 --rate 4M &
   ```
   
2. Receiving at h2: 
   ```bash
   h2 python packet_latency/scapy_files/receive.py
   ```
   
   This will generate the time log of each sending and receiving.

The automation test for large topo is realized in `packet_latency/auto_pkt_latency.py`
