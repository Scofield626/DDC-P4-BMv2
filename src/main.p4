#include <core.p4>
#include <v1model.p4>

#include "includes/header.p4"
#include "includes/metadata.p4"
#include "includes/parser.p4"

#define MAX_LINKS 40
#define MAX_destS 256 // may need modification
#define MAX_DESTINATIONS 256  // may add complexity afterwards

#define IN  1
#define OUT 0

#define down 1
#define up   0

#define PKT_INSTANCE_TYPE_REPLICATION 5
#define PKT_INSTANCE_TYPE_NORMAL 0
#define PKT_INSTANCE_TYPE_INGRESS_RECIRC 4

register<bit<MAX_LINKS>>(MAX_DESTINATIONS) link_directions;
register<bit<MAX_LINKS>>(MAX_DESTINATIONS) to_reverse;
register<bit<MAX_LINKS>>(MAX_DESTINATIONS) local_seqs;
register<bit<MAX_LINKS>>(MAX_DESTINATIONS) remote_seqs;
register<bit<MAX_LINKS>>(1) linkState;
register<bit<8>>(1) linkNum;
register<bit<MAX_LINKS>>(MAX_DESTINATIONS) non_ddc_links; //exclude the border switch's links to hosts(non-ddc-area)
register<bit<8>>(MAX_DESTINATIONS) edge_priorities_0;
register<bit<8>>(MAX_DESTINATIONS) edge_priorities_1;
register<bit<8>>(MAX_DESTINATIONS) edge_priorities_2;
register<bit<8>>(MAX_DESTINATIONS) edge_priorities_3;
register<bit<8>>(MAX_DESTINATIONS) edge_priorities_4;


/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout Parsed_packet pp, inout custom_metadata_t custom_metadata) {
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control update_fib_on_departure(inout custom_metadata_t custom_metadata) {

    bit<MAX_LINKS>  direction_to_reverse;
    bit<MAX_LINKS>  non_ddc_link;

    apply{
        link_directions.read(custom_metadata.link_direction, custom_metadata.dest_seq);
        linkState.read(custom_metadata.linkState, 0);
        linkNum.read(custom_metadata.linkNum, 0);
        non_ddc_links.read(non_ddc_link, custom_metadata.dest_seq);

        if (custom_metadata.link_direction | custom_metadata.linkState | non_ddc_link == ((bit<MAX_LINKS>)1 <<(custom_metadata.linkNum)) - 1) {

            to_reverse.read(direction_to_reverse, custom_metadata.dest_seq);

            if (direction_to_reverse == non_ddc_link) {
                direction_to_reverse = custom_metadata.link_direction;
                to_reverse.write(custom_metadata.dest_seq,direction_to_reverse);
            }
            if (direction_to_reverse == 0) {
                direction_to_reverse = custom_metadata.link_direction;
                to_reverse.write(custom_metadata.dest_seq,direction_to_reverse);
            }

            custom_metadata.link_direction = (custom_metadata.link_direction ^ direction_to_reverse) + non_ddc_link;
            link_directions.write(custom_metadata.dest_seq, custom_metadata.link_direction);

            local_seqs.read(custom_metadata.local_seq, custom_metadata.dest_seq);
            custom_metadata.local_seq = custom_metadata.local_seq ^ direction_to_reverse;
            local_seqs.write(custom_metadata.dest_seq, custom_metadata.local_seq);

            to_reverse.write(custom_metadata.dest_seq, non_ddc_link);
        }
    }
}

control update_fib_on_arrival (inout Parsed_packet pp,
                inout custom_metadata_t custom_metadata,
                inout standard_metadata_t standard_metadata){

    bit<MAX_LINKS> compared_direction;

    action reverse_out_to_in(bit<9> linkindex) {

        link_directions.read(custom_metadata.link_direction, custom_metadata.dest_seq);
        custom_metadata.link_direction = custom_metadata.link_direction ^ ((bit<MAX_LINKS>)1 << ((bit<8>)linkindex - 1));
        link_directions.write(custom_metadata.dest_seq, custom_metadata.link_direction);

        remote_seqs.read(custom_metadata.remote_seq, custom_metadata.dest_seq);
        custom_metadata.remote_seq = custom_metadata.remote_seq ^ ((bit<MAX_LINKS>)1 << ((bit<8>)linkindex - 1));
        remote_seqs.write(custom_metadata.dest_seq, custom_metadata.remote_seq);

    }

    apply{
        /** Note: comparing sequence number should be taken properly
            E.g. 1. Judging a specific bit of link_direction is IN or OUT, shifting left 1 to the XX1XXX, then using OR with original bit strings
                 to create a compared_direction
                 2. Judging if p.seq (one bit) is equal to the corresponding bit of remote_seq, using AND to get the needed bit of remote_seq while masking others
        **/
        link_directions.read(custom_metadata.link_direction, custom_metadata.dest_seq);
        compared_direction = custom_metadata.link_direction | ((bit<MAX_LINKS>)1 << (bit<8>)(standard_metadata.ingress_port-1));

        // check_packetSeq_with_remoteSeq(); // Putting this part into apply block, otherwise the if else condition will be regarded as primitive
        // and it shows nothing about the truly assigned value in log file
        bit<MAX_LINKS> compared_seq;
        remote_seqs.read(custom_metadata.remote_seq, custom_metadata.dest_seq);
        compared_seq = custom_metadata.remote_seq & ((bit<MAX_LINKS>)1 << (bit<8>)(standard_metadata.ingress_port-1)); // Acquire the specific bit

        if (compared_seq != ((bit<MAX_LINKS>)pp.ddc.packetSeq << (bit<8>)(standard_metadata.ingress_port-1))) {
            custom_metadata.pseq_remoteseq_equal = 0;
        } else {
            custom_metadata.pseq_remoteseq_equal = 1;
        }

        if (custom_metadata.link_direction != compared_direction) { // which proves link_direction is OUT
            if (custom_metadata.pseq_remoteseq_equal == 0) {
                reverse_out_to_in(standard_metadata.ingress_port);
            }
        }
    }
}

control choose_outlink_random(inout Parsed_packet pp,
			      inout custom_metadata_t custom_metadata,
			      inout standard_metadata_t standard_metadata) {
    bit<9> port;
    bit<MAX_LINKS> condition;
    bit<MAX_LINKS> compared_condition;

    action do_choose_outlink_random() {
	  
	random(port, 9w1, (bit<9>)custom_metadata.linkNum);	
	condition = custom_metadata.link_direction | custom_metadata.linkState;
	compared_condition = condition | ((bit<MAX_LINKS>)1<<(bit<8>)(port-1));
    }
    
    apply{	
	
	do_choose_outlink_random();

	if (condition != compared_condition) {
	    standard_metadata.egress_spec = port;
	} else {
	    recirculate(pp);	
	}

	bit<MAX_LINKS> current_local_seq;
	local_seqs.read(current_local_seq, custom_metadata.dest_seq);
        pp.ddc.packetSeq = (bit<1>)((current_local_seq & ((bit<MAX_LINKS>)1<<(bit<8>)(port-1))) >> (bit<8>)(port-1));
	pp.ddc.hops_count = pp.ddc.hops_count + 1;
    }
}


control choose_outlink_by_priorities(inout Parsed_packet pp,
				     inout custom_metadata_t custom_metadata,
			             inout standard_metadata_t standard_metadata) {
    bit<9> choosed_port;
    bit<8> edge_priority;
    bit<MAX_LINKS> condition;
    bit<MAX_LINKS> compared_condition;
    
    action do_choose_outlink (bit<9> port) {

        bit<MAX_LINKS> current_local_seq;

        standard_metadata.egress_spec = port;
        local_seqs.read(current_local_seq, custom_metadata.dest_seq);
        pp.ddc.packetSeq = (bit<1>)((current_local_seq & ((bit<MAX_LINKS>)1<<(bit<8>)(port-1))) >> (bit<8>)(port-1));
        pp.ddc.hops_count = pp.ddc.hops_count + 1;
    }

    table choose_outlink {
        key = {
	     custom_metadata.link_direction : ternary;
             custom_metadata.linkState : ternary;
        }
	    actions = {
	        do_choose_outlink;
             	NoAction;
	    }
  	    size = 512;
        default_action = NoAction();
    }

    action set_outlink() {
        
        bit<MAX_LINKS> current_local_seq;

        standard_metadata.egress_spec = choosed_port;
        local_seqs.read(current_local_seq, custom_metadata.dest_seq);
        pp.ddc.packetSeq = (bit<1>)((current_local_seq & ((bit<MAX_LINKS>)1<<(bit<8>)(choosed_port-1))) >> (bit<8>)(choosed_port-1));
        pp.ddc.hops_count = pp.ddc.hops_count + 1;
    }

    apply {
    	edge_priorities_0.read(edge_priority, custom_metadata.dest_seq);
        if (edge_priority != 0) {

            condition = custom_metadata.link_direction | custom_metadata.linkState;
            compared_condition = condition | ((bit<MAX_LINKS>)1 << (edge_priority-1));
        
            if (condition != compared_condition) {
                choosed_port = (bit<9>)edge_priority;
                set_outlink();
            } else {
                edge_priorities_1.read(edge_priority, custom_metadata.dest_seq);
                if (edge_priority != 0) {

                    compared_condition = condition | ((bit<MAX_LINKS>)1 << (edge_priority-1));
        
                    if (condition != compared_condition) {
                        choosed_port = (bit<9>)edge_priority;
                        set_outlink();
                    } else {
                        edge_priorities_2.read(edge_priority, custom_metadata.dest_seq);
                        if (edge_priority != 0) {

                            compared_condition = condition | ((bit<MAX_LINKS>)1 << (edge_priority-1));
                        
                            if (condition != compared_condition) {
                                choosed_port = (bit<9>)edge_priority;
                                set_outlink();
                            } else {
                                edge_priorities_3.read(edge_priority, custom_metadata.dest_seq);
                                if (edge_priority != 0) {

                                    compared_condition = condition | ((bit<MAX_LINKS>)1 << (edge_priority-1)); 
                                
                                    if (condition != compared_condition) {
                                        choosed_port = (bit<9>)edge_priority;
                                        set_outlink();
                                    } else {
                                        edge_priorities_4.read(edge_priority, custom_metadata.dest_seq);
                                        if (edge_priority != 0) {

                                            compared_condition = condition | ((bit<MAX_LINKS>)1 << (edge_priority-1));
                                        
                                            if (condition != compared_condition) {
                                                choosed_port = (bit<9>)edge_priority;
                                                set_outlink();
                                            } else {
                                                choose_outlink.apply();
                                            }
                                        } else {
                                            choose_outlink.apply();
                                        }
                                    }
                                } else {
                                    choose_outlink.apply();
                                }    
                            }
                        } else {
                            choose_outlink.apply();
                        }
                    }
                } else {
                    choose_outlink.apply();
                }
            }
        } else {
            choose_outlink.apply();
        }
    }
}
						


control MyIngress(inout Parsed_packet pp,
                inout custom_metadata_t custom_metadata,
                inout standard_metadata_t standard_metadata) {

    action _drop() {
        mark_to_drop(standard_metadata);
    }

    action set_is_ingress_border() {
        custom_metadata.is_ingress_border = 1w1;
    }

    table check_is_ingress_border {
        key = {
            standard_metadata.ingress_port: exact;
        }
        actions = {
            NoAction;
            set_is_ingress_border;
        }
        default_action = NoAction;
        size = 512;
    }

    action do_add_ddc_header() {
        pp.ethernet.etherType = ETHERTYPE_DDC_UPDATE;
        pp.ddc.setValid();
        pp.ddc.packetSeq = 1w1;
        pp.ddc.hops_count = 32w0;
    }

    table add_ddc_header {
        key = {
            pp.ipv4.dstAddr: lpm;
        }
        actions = {
            NoAction;
            do_add_ddc_header;
        }
        default_action = NoAction();
        size = 512;
    }

    // need to know which destination this DAR is oriented
    action do_get_dest_seq (bit<32> dest_seq) { // since the register has bit<32> index
        custom_metadata.dest_seq = dest_seq;
    } 

    table get_dest_seq {
        key = {
            pp.ipv4.dstAddr: lpm;
        }
        actions = {
            NoAction;
            do_get_dest_seq;
        }
        default_action = NoAction();
        size = 512;
    }

    // initial a sequence number for packet srcaddr, which can be used as index at the egress's hops_number register
    action do_get_src_seq (bit<32> src_seq) {
        custom_metadata.src_seq = src_seq;
    }

    table get_src_seq {
        key = {
            pp.ipv4.srcAddr: lpm;
        }
        actions = {
            NoAction;
            do_get_src_seq;
        }
        default_action = NoAction();
        size = 512;
    }    

    action do_choose_outlink (bit<9> port) {

        bit<MAX_LINKS> current_local_seq;

        standard_metadata.egress_spec = port;
        local_seqs.read(current_local_seq, custom_metadata.dest_seq);
        pp.ddc.packetSeq = (bit<1>)((current_local_seq & ((bit<MAX_LINKS>)1<<(bit<8>)(port-1))) >> (bit<8>)(port-1));
        //pp.ddc.packetSeq = current_local_seq[port:port]; ---> wrong cuz the slice [] needed parameters which are compilation-time integeres

        pp.ddc.hops_count = pp.ddc.hops_count + 1;
    }

    table choose_outlink {
        key = {
	     custom_metadata.link_direction : ternary;
             custom_metadata.linkState : ternary;
        }
	    actions = {
	        do_choose_outlink;
             	NoAction;
	    }
  	    size = 512;
        default_action = NoAction();
    }


    action ipv4_forward(EthernetAddress dstAddr, egressSpec_t port) {
        pp.ethernet.srcAddr = pp.ethernet.dstAddr;
        pp.ethernet.dstAddr = dstAddr;
        standard_metadata.egress_spec = port;
        pp.ipv4.ttl = pp.ipv4.ttl - 1;
    }

    table ipv4_lpm {
        key = {
            pp.ipv4.dstAddr: lpm;
        }
        actions = {
            ipv4_forward;
            _drop;
            NoAction;
        }
        default_action = NoAction();
        size = 512;
    }

    //counter(512, CounterType.packets_and_bytes) port_counter;

    apply{

        //check if it is a ingress border port
        if (standard_metadata.instance_type == PKT_INSTANCE_TYPE_NORMAL) {
            check_is_ingress_border.apply();

            if (custom_metadata.is_ingress_border == 1){
                if (pp.ipv4.isValid()) {
                    add_ddc_header.apply();
                }
            }
   	}

        if (pp.ddc.isValid()) {

            get_dest_seq.apply();
            get_src_seq.apply();
            //initialize to_reverse

            update_fib_on_arrival.apply(pp, custom_metadata, standard_metadata); // parameter?

            link_directions.read(custom_metadata.link_direction, custom_metadata.dest_seq);
            to_reverse.write(custom_metadata.dest_seq, custom_metadata.link_direction);

            update_fib_on_departure.apply(custom_metadata);// ingress or egress

            link_directions.read(custom_metadata.link_direction, custom_metadata.dest_seq);
            bit<MAX_LINKS> compared_direction;
            compared_direction = custom_metadata.link_direction | ((bit<MAX_LINKS>)1 << (bit<8>)(standard_metadata.ingress_port-1));

            linkState.read(custom_metadata.linkState, 0);
            #choose_outlink.apply();// send_on_outlink(any outlink, packet)
	    #choose_outlink_random.apply(pp, custom_metadata, standard_metadata);
            choose_outlink_by_priorities.apply(pp, custom_metadata, standard_metadata);
            
            bit<MAX_LINKS> local_seq;
            //Bouncing back (can be put before above 2 lines, send_to_egress)
            if (custom_metadata.link_direction != compared_direction) { // if link direction is OUT
                if (custom_metadata.pseq_remoteseq_equal == 1) { // bounce back, there is a typo in original paper
                    // no new sequence number means that the neighbor has the stale info, so bounce back to it for update
                    // swap_mac(); whether it is unneeded
            	    standard_metadata.egress_spec = standard_metadata.ingress_port;
                    local_seqs.read(local_seq, custom_metadata.dest_seq);
                    pp.ddc.packetSeq = (bit<1>)((local_seq & ((bit<MAX_LINKS>)1<<(bit<8>)(standard_metadata.egress_spec-1))) >> ((bit<8>)standard_metadata.egress_spec-1));
                }
            }

        } else if (pp.ipv4.isValid()){
            //implement normal forwarding
            ipv4_lpm.apply();
        }
    }

}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout Parsed_packet pp,
                inout custom_metadata_t custom_metadata,
                inout standard_metadata_t standard_metadata) {

    register<bit<32>>(MAX_DESTINATIONS) hops_number;

    action set_is_egress_border(){

        hops_number.write(custom_metadata.src_seq, pp.ddc.hops_count);
        pp.ddc.setInvalid();
        pp.ethernet.etherType = ETHERTYPE_IPV4;
        recirculate(pp);

    }

    table check_is_egress_border {
        key = {
            standard_metadata.egress_port: exact;
        }
        actions = {
            NoAction;
            set_is_egress_border;
        }
        default_action = NoAction;
        size = 512;
    }

    apply {
        // We check if it is an egress border port
        if (pp.ddc.isValid()){
            check_is_egress_border.apply();
        }
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout Parsed_packet pp, inout custom_metadata_t custom_meta) {
    apply {
    	update_checksum(
            pp.ipv4.isValid(),
                { pp.ipv4.version,
                  pp.ipv4.ihl,
                  pp.ipv4.dscp,
                  pp.ipv4.ecn,
                  pp.ipv4.totalLen,
                  pp.ipv4.identification,
                  pp.ipv4.flags,
                  pp.ipv4.fragOffset,
                  pp.ipv4.ttl,
                  pp.ipv4.protocol,
                  pp.ipv4.srcAddr,
                  pp.ipv4.dstAddr },
            pp.ipv4.hdrChecksum,
            HashAlgorithm.csum16);

        update_checksum(
            pp.tcp.isValid(),
              { pp.tcp.srcPort,
                pp.tcp.dstPort,
                pp.tcp.seqNo,
                pp.tcp.ackNo,
                pp.tcp.dataOffset,
                pp.tcp.res,
                pp.tcp.cwr,
                pp.tcp.ece,
                pp.tcp.urg,
                pp.tcp.ack,
                pp.tcp.psh,
                pp.tcp.rst,
                pp.tcp.syn,
                pp.tcp.fin,
                pp.tcp.window,
                pp.tcp.urgentPtr},
            pp.tcp.checksum,
            HashAlgorithm.csum16);

        update_checksum(
            pp.udp.isValid(),
                { pp.udp.srcPort,
                  pp.udp.dstPort,
                  pp.udp.len},
            pp.udp.checksum,
            HashAlgorithm.csum16);
   }
}


/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in Parsed_packet pp) {
    apply {
        packet.emit(pp.ethernet);
        packet.emit(pp.ddc);
        packet.emit(pp.ipv4);
        packet.emit(pp.tcp);
        packet.emit(pp.udp);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

//switch architecture
V1Switch(
    ParserImpl(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()) main;
