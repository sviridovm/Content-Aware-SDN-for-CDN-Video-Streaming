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


header cdn__req_t {
    bit<32> video_id;
    bit<32> chunk_id;
}



struct headers {
    ethernet_t ethernet;
//    ipv4_t ipv4;
//    tcp_t tcp;
    cdn_t cdn_req;
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
        packet.extract(hdr.cdn);
        meta.videoID = hdr.cdn.video_id;
        meta.chunkID = hdr.cdn.chunk_id;
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
        hdr.packet_in.setValid();
        hdr.packet_in.ingress_port = standard_metadata.ingress_port;
    }

    action forward_to_default_cdn() {
        standard_metadata.egress_spec = 0; // what is the correct egress_port?
    }

    action drop() {
        mark_to_drop(standard_metadata);
    }


    table mac_forward {
        key = {
            hdr.ethernet.dstAddr: exact;
        }

        actions = {
            forward;
            drop;
        }

        size = 1024;
        default_action = drop;
    }

    table cdn_table {
        key = {
            meta.videoID: exact;
            meta.chunkID: exact;
        }

        actions = {
            forward;
            forward_to_default_cdn;
        }

        size = 1024;
        default_action = forward_to_default_cdn;
    }


    apply {

        if(hdr.ethernet.etherType == ETH_TYPE_MSG_TO_CONTROLLER) {
            to_controller();
            return;
        }


        if (hdr.cdn.isValid()) {
            cdn_table.apply();
            return;
        }

        mac_forward.apply();


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

    action to_controller() {
        hdr.packet_in.setValid();
        hdr.packet_in.ingress_port = standard_metadata.ingress_port;
    }

    apply { 

        if (standard_metadata.egress_port == standard_metadata.ingress_port) {
            drop();
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


