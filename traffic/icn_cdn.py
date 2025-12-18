import json
import time
from flask import Response, abort
from collections import OrderedDict

import argparse
import threading
import queue

from util import request_video_no_response, VideoResponse, listen_for_video_requests, send_update_to_controller, send_video_response
from util import request_video

from scapy.all import Ether, sendp, Packet
from scapy.all import AsyncSniffer

from queue import Queue


metadata = json.load(open("topo/topo.json"))

ORIGIN_MAC = metadata["hosts"]["origin"]["mac"]

CACHE_SIZE = 100                               # number of chunks
CACHE = OrderedDict()                          # (video_id, chunk_id) -> Response
CACHE_LOCK = threading.Lock()

CHUNKS_TO_ADD = queue.Queue()
CHUNKS_TO_REMOVE = queue.Queue()

CHUNK_FULFILLMENT_MAP = {}  # (video_id, chunk_id) -> threading.Event()
CHUNK_FULFILLMENT_MAP_LOCK = threading.Lock()



my_mac = None
host_name = None


def update_controller():
    
    additions = get_chunks_to_add()
    removals = get_chunks_to_remove()
    
    if additions:
        # print(f"CDN {cdn_id} adding chunks: {additions}")
        send_update_to_controller(additions, action="add", host=host_name)
    if removals:
        # print(f"CDN {cdn_id} removing chunks: {removals}")
        send_update_to_controller(removals, action="rem", host=host_name)

def get_chunks_to_remove():
    removals = []
    while not CHUNKS_TO_REMOVE.empty():
        removals.append(CHUNKS_TO_REMOVE.get())
    return removals

def get_chunks_to_add():
    additions = []
    while not CHUNKS_TO_ADD.empty():
        additions.append(CHUNKS_TO_ADD.get())
    return additions   
    
    
def periodic_update():
    while True:
        try:
            update_controller()
            threading.Event().wait(1) 
        except KeyboardInterrupt:
            return



def fetch_chunk(video_id, chunk_id) -> bytes:
    cache_key = (video_id, chunk_id)


    print("fetching video {0} chunk {1}".format(video_id, chunk_id), "from cache")

    
    with CACHE_LOCK:
        # Check cache
        if cache_key in CACHE:
            print(f"Cache HIT: video {video_id} chunk {chunk_id} data {CACHE[cache_key]}")
            CACHE.move_to_end(cache_key)  # promote to MRU
            return CACHE[cache_key]
    
    print(f"Cache MISS: video {video_id} chunk {chunk_id}, fetching from origin...")
    
    
    request_video_no_response(
        dst_mac_addr=ORIGIN_MAC,
        src_mac_addr=my_mac,
        video_id=video_id,
        chunk_id=chunk_id,
        from_origin=True,
        host=host_name
    )
    
    with CHUNK_FULFILLMENT_MAP_LOCK:
        if cache_key not in CHUNK_FULFILLMENT_MAP:
            CHUNK_FULFILLMENT_MAP[cache_key] = threading.Event()
    
    return None

    
    
def serve_chunk(video_id, chunk_id, request_pkt: Packet):
    data = fetch_chunk(video_id, chunk_id)
    dst_mac = request_pkt[Ether].src
    
    if data is None:
        threading.Thread(
            target=send_cache_miss_response,
            args=(dst_mac, video_id, chunk_id, data),
            daemon=True
        ).start()
        return

    print(f"CDN server: Serving video {video_id} chunk {chunk_id} to MAC {dst_mac}") 

    send_video_response(
        dst_mac_addr=dst_mac,
        video_id=video_id,
        chunk_id=chunk_id,
        data=data,
        from_origin=False,
        host=host_name
    )
    
    print("sent cached response")
    
    
def handle_response_callback(response_pkt: Packet):
    video_resp = response_pkt[VideoResponse]
    video_id = video_resp.video_id
    chunk_id = video_resp.chunk_id
    data = video_resp.data
    print(f"Received video response: video_id={video_id}, chunk_id={chunk_id}, data_length={len(data)}")


def send_cache_miss_response(dst_mac_addr: str, video_id: int, chunk_id: int, data: bytes):
    with CHUNK_FULFILLMENT_MAP_LOCK:
        cache_key = (video_id, chunk_id)
        if cache_key not in CHUNK_FULFILLMENT_MAP:
            # CHUNK_FULFILLMENT_MAP[cache_key] = threading.Event()
            return
        event = CHUNK_FULFILLMENT_MAP[cache_key]
        
    received = event.wait(timeout=10)  # wait for up to 10 seconds

    print("Cache miss response: received =", received)

    
    if not received:
        data = bytes()

    
    with CACHE_LOCK:
        data = CACHE.get(cache_key, None)

        if data is None:
            print(f"Failed to fetch video {video_id} chunk {chunk_id} from origin")
            return bytes()

        # Evict if over capacity
        if len(CACHE) > CACHE_SIZE:
            evicted_key, _ = CACHE.popitem(last=False)
            CHUNKS_TO_REMOVE.put(evicted_key)
                
            print(f"Evicted LRU chunk: video {evicted_key[0]} chunk {evicted_key[1]}")



    print(f"Origin server: Serving video {video_id} chunk {chunk_id} to MAC {dst_mac_addr}") 

    send_video_response(
        dst_mac_addr=dst_mac_addr,
        video_id=video_id,
        chunk_id=chunk_id,
        data=data,
        from_origin=False,
        host=host_name
    )

def add_chunk_to_cache(video_id, chunk_id, data: bytes):
    cache_key = (video_id, chunk_id)
    
    with CACHE_LOCK:
        if cache_key in CACHE:
            return  # already in cache
        
        CACHE[cache_key] = data
        CACHE.move_to_end(cache_key)  # promote to MRU
        CHUNKS_TO_ADD.put(cache_key)
        print("adding", data, "to cache for video", video_id, "chunk", chunk_id)

    with CHUNK_FULFILLMENT_MAP_LOCK:
        if cache_key in CHUNK_FULFILLMENT_MAP:
            event = CHUNK_FULFILLMENT_MAP[cache_key]
            event.set()
            del CHUNK_FULFILLMENT_MAP[cache_key]
            

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="CDN Server")
    parser.add_argument("--id", type=str, required=True, help="CDN ID")
    args = parser.parse_args()

    host_name = f"{args.id}"
    my_mac = metadata["hosts"][host_name]["mac"]
    print(f"My MAC address: {my_mac}")
  
    
    update_thread = threading.Thread(target=periodic_update, daemon=True)
    update_thread.start()
    
    print("CDN Server started listening for video requests...")
    print("Press Ctrl+C to stop.")
    
    try:
        listen_for_video_requests(
            is_origin=False,
            handle_request_callback=serve_chunk,
            handle_response_callback=add_chunk_to_cache,
            host=f"{args.id}"
        )
    
    except KeyboardInterrupt:
        pass
    
                
    print("CDN Server stopped.")    

