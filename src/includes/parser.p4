#define ETHERTYPE_IPV4                      16w0x800
#define ETHERTYPE_DDC_UPDATE                16w0x1234  // not sure
#define IP_PROTOCOLS_TCP                    8w6
#define IP_PROTOCOLS_UDP                    8w11


parser ParserImpl(packet_in pkt_in, out Parsed_packet pp,
    inout custom_metadata_t meta,
    inout standard_metadata_t standard_metadata) {

    state start {
        pkt_in.extract(pp.ethernet);
        transition select(pp.ethernet.etherType) {
            ETHERTYPE_IPV4: parse_ipv4;
            ETHERTYPE_DDC_UPDATE: parse_ddc;
            default: accept;
        }
    }

    state parse_ddc {
        pkt_in.extract(pp.ddc);
        transition parse_ipv4;
    }

    state parse_ipv4 {
        pkt_in.extract(pp.ipv4);
        transition select(pp.ipv4.protocol) {
            IP_PROTOCOLS_TCP: parse_tcp;
            IP_PROTOCOLS_UDP: parse_udp;
            default: accept;
        }
    }

    state parse_tcp {
        pkt_in.extract(pp.tcp);
        transition accept;
    }

    state parse_udp {
        pkt_in.extract(pp.udp);
        transition accept;
    }
}
