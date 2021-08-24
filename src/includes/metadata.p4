#define MAX_LINKS 40
#define MAX_DESTINATIONS 256
struct custom_metadata_t {
    bit<MAX_LINKS>  local_seq;
    bit<MAX_LINKS>  remote_seq;
    bit<MAX_LINKS> link_direction;
    bit<1>  pseq_remoteseq_equal; //whether packetSeq and remote_seq are equal
    bit<32>  dest_seq;
    bit<32>  src_seq;
    bit<1> is_ingress_border;
    bit<1> is_egress_border;
    bit<MAX_LINKS> destination;
    bit<MAX_LINKS> linkState;
    bit<8> linkNum;
}
