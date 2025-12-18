import socket
import scapy
from scapy.all import Ether, sendp, Raw, Packet, sniff
from scapy.fields import IntField, StrField
from scapy.all import bind_layers
from scapy.all import AsyncSniffer

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
        StrField("data", b""),
    ]

bind_layers(Ether, VideoRequest, type=ETH_TYPE_REQ_TO_ORGN)
bind_layers(Ether, VideoResponse, type=ETH_TYPE_RESP_FROM_ORGN)
bind_layers(Ether, VideoResponse, type=ETH_TYPE_RESP_FROM_CDN)
bind_layers(Ether, VideoRequest, type=ETH_TYPE_REQ_TO_CDN)


def request_video(dst_mac_addr: str, src_mac_addr: str, video_id: int, chunk_id: int, from_origin: bool, host: str) -> bytes:
    eth = Ether(dst=dst_mac_addr, type=ETH_TYPE_REQ_TO_ORGN if from_origin else ETH_TYPE_REQ_TO_CDN, src=src_mac_addr)
    packet = eth / VideoRequest(
        video_id=video_id,
        chunk_id=chunk_id
    )
    
    
    iface_name = f"{host}-eth1"
    
    print("interface_name:", iface_name)
    
    # Send packet and wait for response
    sendp(packet, iface=iface_name, verbose=False)

    def is_video_response(pkt):
        return (
            pkt.haslayer(Ether)
            and pkt[Ether].type == (ETH_TYPE_RESP_FROM_ORGN if from_origin else ETH_TYPE_RESP_FROM_CDN)
            and pkt.haslayer(VideoResponse)
        )



    received_response = False
    response = bytes()


    def handle_packet(pkt: Packet):
        pkt.show()
        resp = pkt[VideoResponse]
        video_id = resp.video_id
        chunk_id = resp.chunk_id
        data = resp.data
        print(f"Received video response: video_id={video_id}, chunk_id={chunk_id}, data_length={len(data)}")
        nonlocal received_response
        received_response = True
        
        nonlocal response
        response = data


    sniff(
        iface=iface_name,
        lfilter=is_video_response,
        prn=handle_packet,
        timeout=5,
    )
    
    
    if not received_response:
        print("No response received for the video request.")
        return bytes()
    else:
        return response

def request_video_no_response(dst_mac_addr: str, src_mac_addr: str, video_id: int, chunk_id: int, from_origin: bool, host: str):
    eth = Ether(dst=dst_mac_addr, type=ETH_TYPE_REQ_TO_ORGN if from_origin else ETH_TYPE_REQ_TO_CDN, src=src_mac_addr)
    packet = eth / VideoRequest(
        video_id=video_id,
        chunk_id=chunk_id
    )
    
    
    iface_name = f"{host}-eth1"
    
    print("interface_name:", iface_name)
    
    # Send packet without waiting for response
    sendp(packet, iface=iface_name, verbose=False)




def listen_for_video_requests(is_origin: bool, handle_request_callback, handle_response_callback, host: str):
    ETH_TYPE = ETH_TYPE_REQ_TO_ORGN if is_origin else ETH_TYPE_REQ_TO_CDN

    def is_video_request(pkt: Packet):
        return (
            pkt.haslayer(Ether)
            and pkt[Ether].type == ETH_TYPE
            and pkt.haslayer(VideoRequest)
        )

    def is_video_response(pkt: Packet):
        return (
            pkt.haslayer(Ether)
            and pkt[Ether].type == (ETH_TYPE_RESP_FROM_ORGN)
            and pkt.haslayer(VideoResponse)
        )
        
        
    def filter_packet(pkt: Packet):
        return is_video_request(pkt) or is_video_response(pkt)



    def process_packet(pkt: Packet):
        if is_video_request(pkt):
            process_request_packet(pkt)
        elif is_video_response(pkt) and handle_response_callback is not None:
            process_response_packet(pkt)


    def process_request_packet(pkt: Packet):
        print("Processing request packet:")
        pkt.show()
        video_req = pkt[VideoRequest]
        video_id = video_req.video_id
        chunk_id = video_req.chunk_id
        print(f"Received video request: video_id={video_id}, chunk_id={chunk_id}")
        handle_request_callback(video_id, chunk_id, pkt)

    def process_response_packet(pkt: Packet):
        print("Processing response packet:")
        pkt.show()
        video_resp = pkt[VideoResponse]
        video_id = video_resp.video_id
        chunk_id = video_resp.chunk_id
        data = video_resp.data
        print(f"Received video response: video_id={video_id}, chunk_id={chunk_id}, data_length={len(data)}")
        handle_response_callback(video_id, chunk_id, data)
    


        
    sniff(
        iface=f"{host}-eth1",
        prn=process_packet,
        lfilter=filter_packet,
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
    




