import os

from flask import json
from scapy.all import Packet, Ether
from util import VideoRequest, listen_for_video_requests, send_video_response

VIDEO_DIR = "/workdir/video"


def fetch_chunk_from_disk(video_id, chunk_id) -> bytes:
    path = os.path.join(VIDEO_DIR, f"{video_id}/{chunk_id}.bin")
    if not os.path.exists(path):
        return bytes()
    with open(path, "rb") as f:
        return f.read()
    

def serve_chunk(video_id, chunk_id, request_pkt: Packet):
    data = fetch_chunk_from_disk(video_id, chunk_id)
    if data is None:
        print(f"Origin server: video {video_id} chunk {chunk_id} not found")
        return
    else:
        print("Data is", data)


    dst_mac = request_pkt[Ether].src
    print(f"Origin server: Serving video {video_id} chunk {chunk_id} to MAC {dst_mac}") 


    send_video_response(
        dst_mac_addr=dst_mac,
        video_id=video_id,
        chunk_id=chunk_id,
        data=data,
        from_origin=True,
        host="origin"
    )

if __name__ == "__main__":
    # config = json.loads(open("topo/topo.json").read())


    try: 
        listen_for_video_requests(
            is_origin=True,
            handle_request_callback=serve_chunk,
            handle_response_callback=None,
            host="origin"
        )
    except KeyboardInterrupt:
        pass

        
    
