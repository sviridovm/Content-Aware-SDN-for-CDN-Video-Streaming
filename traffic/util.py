import socket
from urllib import response
from flask import Response, abort, send_file
import scapy
from scapy.all import Ether, sendp, Raw, Packet, sniff
from scapy.fields import IntField, StrLenField
from scapy.all import bind_layers

ETH_TYPE_REQ_TO_ORGN = 0x88B6
ETH_TYPE_MSG_TO_CONTROLLER = 0x88B5
ETH_TYPE_RESP_FROM_ORGN = 0x88B7
ETH_TYPE_RESP_FROM_CDN = 0x88B8
ETH_TYPE_REQ_TO_CDN = 0x88B9


class VideoRequest(Packet):
    name = "VideoRequest"
    fields_desc = [
        IntField("video_id", 0),
        IntField("chunk_id", 0),
    ]
    
class VideoResponse(Packet):
    name = "VideoResponse"
    fields_desc = [
        IntField("video_id", 0),
        IntField("chunk_id", 0),
        StrLenField("data", b"", length_from=lambda pkt: len(pkt.data)),
    ]

bind_layers(Ether, VideoRequest, type=ETH_TYPE_REQ_TO_ORGN)
bind_layers(Ether, VideoResponse, type=ETH_TYPE_RESP_FROM_ORGN)
bind_layers(Ether, VideoResponse, type=ETH_TYPE_RESP_FROM_CDN)
bind_layers(Ether, VideoRequest, type=ETH_TYPE_REQ_TO_CDN)


def is_video_response(pkt):
    return (
        pkt.haslayer(Ether)
        and pkt[Ether].type in {ETH_TYPE_RESP_FROM_ORGN, ETH_TYPE_RESP_FROM_CDN}
        and pkt.haslayer(VideoResponse)
    )


def request_video(dst_mac_addr: str, video_id: int, chunk_id: int, from_origin: bool, host: str) -> Response:
    eth = Ether(dst=dst_mac_addr, type=ETH_TYPE_REQ_TO_ORGN if from_origin else ETH_TYPE_REQ_TO_CDN)
    packet = eth / Raw(
        IntField("video_id", video_id) /
        IntField("chunk_id", chunk_id)
    )
    
    
    iface_name = f"{host}-eth1"
    # Send packet and wait for response
    sendp(packet, iface=iface_name, verbose=False, timeout=2)



    pkts = sniff(
    iface=iface_name,
    lfilter=is_video_response,
    timeout=5,
    count=1)

    if not pkts:
        print("No response received")
        abort(504)

    
    resp = pkts[0][VideoResponse]

    print("video_id:", resp.video_id)
    print("chunk_id:", resp.chunk_id)
    data = resp.data
    chunk_data = scapy.compat.BytesIO(data)

    return send_file(chunk_data)



def listen_for_video_requests(is_origin: bool, handle_request_callback, host: str):
    ETH_TYPE = ETH_TYPE_REQ_TO_ORGN if is_origin else ETH_TYPE_REQ_TO_CDN

    def is_video_request(pkt: Packet):
        return (
            pkt.haslayer(Ether)
            and pkt[Ether].type == ETH_TYPE
            and pkt.haslayer(VideoRequest)
        )

    def process_packet(pkt: Packet):
        if is_video_request(pkt):
            video_req = pkt[VideoRequest]
            video_id = video_req.video_id
            chunk_id = video_req.chunk_id
            print(f"Received video request: video_id={video_id}, chunk_id={chunk_id}")
            handle_request_callback(video_id, chunk_id, pkt)

    sniff(
        iface=f"{host}-eth1",
        prn=process_packet,
        lfilter=is_video_request,
        store=0
    )
    
def send_video_response(dst_mac_addr: str, video_id: int, chunk_id: int, data: bytes, from_origin: bool, host: str):
    eth = Ether(dst=dst_mac_addr, type=ETH_TYPE_RESP_FROM_ORGN if from_origin else ETH_TYPE_RESP_FROM_CDN)
    packet = eth / VideoResponse(
        video_id=video_id,
        chunk_id=chunk_id,
        data=data
    )
    sendp(packet, iface=f"{host}-eth1", verbose=False)
    
    
from itertools import islice
def send_update_to_controller(chunk_list: list, action: str, host: str):
    eth = Ether(dst="ff:ff:ff:ff:ff:ff", type=ETH_TYPE_MSG_TO_CONTROLLER)
    packet = eth
    
    
    chunks_per_packet = 10
    
    islice_iter = iter(chunk_list)
    for _ in range(0, len(chunk_list), chunks_per_packet):
        chunk_subset = list(islice(islice_iter, chunks_per_packet))
        chunk_ids_bytes = f'{action}'.encode() 
        for video_id, chunk_id in chunk_subset:
            chunk_ids_bytes += video_id.to_bytes(4, byteorder='big') + chunk_id.to_bytes(4, byteorder='big')
        
        
        packet_with_chunks = packet / chunk_ids_bytes
        sendp(packet_with_chunks, iface=f"{host}-eth1", verbose=False)
    




