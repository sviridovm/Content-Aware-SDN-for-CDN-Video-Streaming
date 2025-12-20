/*****************************************************************************
 *
 *  switch
 *
 *****************************************************************************/

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

register<bit<32>>(1) rr_index;
const bit<32> NUM_PORTS = 3;



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
/**
header ipv4_t {
    bit<4>  version;
    bit<4>  ihl;
    bit<8>  diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3>  flags;
    bit<13> fragOffset;
    bit<8>  ttl;
    bit<8>  protocol;
    bit<16> hdrChecksum;
    bit<32> srcAddr;
    bit<32> dstAddr;
}
**/


/**
header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<4>  res;
    bit<8>  flags;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}
**/


header cdn_req_t {
    bit<32> videoID;
    bit<32> chunkID;
}

struct metadata {

}


struct headers {
    ethernet_t ethernet;
//    ipv4_t ipv4;
//    tcp_t tcp;
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


    /**
    state parse_tcp {
        packet.extract(hdr.tcp);
        transition select(hdr.tcp.dstPort) {
            CDN_PORT: parse_msg_type;
            default: accept;
        }
    }
    **/

    /**
    state parse_msg_type {
        packet.extract(hdr.msg_type);
        transition select(hdr.msg_type.signature) {
            REQUEST_BYTE_SIGNATURE: parse_cdn;
            //RESPONSE_BYTE_SIGNATURE: accept;
            //ORIGIN_BYTE_SIGNATURE: accept;
            default: accept;
        }
    }
    **/

    state parse_cdn {
        packet.extract(hdr.cdn_req);
        //meta.videoID = hdr.cdn_req.video_id;
        //meta.chunkID = hdr.cdn_req.chunk_id;
        transition accept;
    }
    
    /**
    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            6: parse_tcp; // TCP protocol
            default: accept;
        }
    }
    **/

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

    action forward(egressSpec_t port) {
        standard_metadata.egress_spec = port;
    }

    action to_controller() {
        standard_metadata.egress_spec = CPU_PORT;
        hdr.packet_in.setValid();
        hdr.packet_in.ingress_port = standard_metadata.ingress_port;
    }

   

    action forward_to_default_cdn() {
        standard_metadata.egress_spec = 2; // what is the correct egress_port?
    }

    action round_robin_select() {
        bit<32> idx;
        rr_index.read(idx, 0);

        // Map index → egress port
        if (idx == 0) {
            standard_metadata.egress_spec = 2;
        } else if (idx == 1) {
            standard_metadata.egress_spec = 3;
        } else {
            standard_metadata.egress_spec = 4;
        }

        // Update index
        bit<32> next = idx + 1;
        if (next >= NUM_PORTS) {
            next = 0;
        }
        rr_index.write(0, next);
    }


    action drop() {
        mark_to_drop(standard_metadata);
    }

    action flood() {
        standard_metadata.egress_spec = 0x1FF; // BMv2 flood
    }

    action noop() {

    }


    table mac_forward {
        key = {
            hdr.ethernet.dstAddr: exact;
        }

        actions = {
            forward;
            flood;
        }

        size = 1024;
        default_action = flood();
    }

    table cdn_table {
        key = {
            hdr.cdn_req.videoID: exact;
            hdr.cdn_req.chunkID: exact;
        }

        actions = {
            forward;
            //forward_to_default_cdn;
            round_robin_select;
        }

        size = 1024;
        default_action = round_robin_select;
        //default_action = forward_to_default_cdn;
    }


    apply {
        
        if(hdr.ethernet.etherType == ETH_TYPE_MSG_TO_CONTROLLER) {
            to_controller();
            return;
        }

        if (hdr.ethernet.etherType == ETH_TYPE_REQ_TO_CDN) {
            cdn_table.apply();
            return;
        }

        if(hdr.ethernet.etherType == ETH_TYPE_REQ_TO_ORGN
        || hdr.ethernet.etherType == ETH_TYPE_RESP_FROM_CDN
        || hdr.ethernet.etherType == ETH_TYPE_RESP_FROM_ORGN) {
            mac_forward.apply();
            return;
        }

        drop();


    }
}

/**************************************************************************/
/************************  Egress Processing  *****************************/
/**************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
                 

    action noop() { }   

    action drop() {
        mark_to_drop(standard_metadata);
    }

    apply { 

        if (standard_metadata.egress_port == standard_metadata.ingress_port) {
            drop();
            return;
        } 


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
        packet.emit(hdr.cdn_req);


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


