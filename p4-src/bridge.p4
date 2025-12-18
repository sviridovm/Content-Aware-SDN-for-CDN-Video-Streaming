/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

#define MCAST_ID 1
#define CPU_PORT 255
/*
  255 is confirmed for opennetworking/p4mn　(Mininet/Stratum on docker)
  192 is confirmed for WEDGE-100BF-32X (2 pipes device)
  320 is probably good for 4 pipes devices
*/

#define ETH_TYPE_IPv4 0x0800
#define ETH_TYPE_REQ_TO_CDN 0x88B9 
#define ETH_TYPE_RESP_FROM_CDN 0x88B8
#define ETH_TYPE_REQ_TO_ORGN 0x88B6
#define ETH_TYPE_RESP_FROM_ORGN 0x88B7


#define ETH_TYPE_MSG_TO_CONTROLLER 0x88B5

#define ETH_TYPE_ARP 0x0806


typedef bit<9> egressSpec_t;
typedef bit<48> macAddr_t;

/**************************************************************************/
/**************************  Headers  *************************************/
/**************************************************************************/

@controller_header("packet_in")
header packet_in_header_t {
    bit<9> ingress_port;
    bit<7> _pad;
}

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16> etherType;
}

header cdn_req_t {
    bit<32> videoID;
    bit<32> chunkID;
}

struct metadata {}

struct headers {
    ethernet_t ethernet;
    cdn_req_t cdn_req;
    packet_in_header_t packet_in;
}

/**************************************************************************/
/***************************  Parser  *************************************/
/**************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            ETH_TYPE_REQ_TO_CDN: parse_cdn;

            default: accept;
        }
    }

    state parse_cdn {
        packet.extract(hdr.cdn_req);
        //meta.videoID = hdr.cdn_req.video_id;
        //meta.chunkID = hdr.cdn_req.chunk_id;
        transition accept;
    }

}

/**************************************************************************/
/*********************  Checksum Verification  *****************************/
/**************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

/**************************************************************************/
/***********************  Ingress Processing  *****************************/
/**************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action flood() {
        standard_metadata.mcast_grp = MCAST_ID;
    }

    action forward(egressSpec_t port) {
        standard_metadata.egress_spec = port;
    }

    action forward_to_default_cdn() {
        standard_metadata.egress_spec = 1; // what is the correct egress_port?
    }

    table cdn_table {
        key = {
            hdr.cdn_req.videoID: exact;
            hdr.cdn_req.chunkID: exact;
        }

        actions = {
            forward;
            forward_to_default_cdn;
        }

        size = 1024;
        default_action = forward_to_default_cdn;
    }

   

    action to_controller() {
        standard_metadata.egress_spec = CPU_PORT;
        hdr.packet_in.setValid();
        hdr.packet_in.ingress_port = standard_metadata.ingress_port;
    }


    table bridge_table {
        key = {
            hdr.ethernet.dstAddr: exact;
            standard_metadata.ingress_port: exact;
        }
        actions = {
            drop;
            flood;
        }
        size = 1024;
        default_action = flood;
    }
    
    apply {


        if(hdr.ethernet.etherType == ETH_TYPE_MSG_TO_CONTROLLER) {
            to_controller();
            return;
        }

        if(hdr.ethernet.etherType == ETH_TYPE_REQ_TO_CDN) {
            cdn_table.apply();
            return;
        }

        if(hdr.ethernet.etherType == ETH_TYPE_ARP) {
            bridge_table.apply();
        } 

    }
}

/**************************************************************************/
/************************  Egress Processing  *****************************/
/**************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    action drop() {
        mark_to_drop(standard_metadata);
    }

    action to_controller() {
        hdr.packet_in.setValid();
        hdr.packet_in.ingress_port = standard_metadata.ingress_port;
    }

    apply {
        // Prune multicast packets going to ingress port to prevent loops
        if (standard_metadata.egress_port == standard_metadata.ingress_port)
            drop();

        // Send a copy of the packet to the controller for learning
        if (standard_metadata.egress_port == CPU_PORT)
            to_controller();
    }
}

/**************************************************************************/
/*********************  Checksum Computation  *****************************/
/**************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

/**************************************************************************/
/**************************  Deparser  ************************************/
/**************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.packet_in);
        packet.emit(hdr.ethernet);

       // packet.emit(hdr.ipv4);

    // packet.emit(hdr.tcp);



    }
}

/**************************************************************************/
/***************************  Switch  *************************************/
/**************************************************************************/

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;


