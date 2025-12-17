import json
from flask import Response, abort
from collections import OrderedDict

import argparse
import threading
import queue

from traffic.util import ETH_TYPE_MSG_TO_CONTROLLER, listen_for_video_requests, send_update_to_controller, send_video_response
from traffic.util import request_video

from scapy.all import Ether, sendp, Packet


metadata = json.load(open("topo/topo.json"))

ORIGIN_MAC = metadata["hosts"]["h0"]["mac"]

CACHE_SIZE = 100                               # number of chunks
CACHE = OrderedDict()                          # (video_id, chunk_id) -> bytes

CHUNKS_TO_ADD = queue.Queue()
CHUNKS_TO_REMOVE = queue.Queue()


# def serve_chunk(video_id, chunk_id) -> Response:
#     cache_key = (video_id, chunk_id)

#     # Check cache
#     if cache_key in CACHE:
#         print(f"Cache HIT: video {video_id} chunk {chunk_id}")
#         CACHE.move_to_end(cache_key)  # promote to MRU
#         return Response(CACHE[cache_key], mimetype="video/mp4")

#     print(f"Cache MISS: video {video_id} chunk {chunk_id}, fetching from origin...")

    
#     resp = request_video(
#         dst_mac_addr=ORIGIN_MAC,
#         video_id=video_id,
#         chunk_id=chunk_id,
#         from_origin=True
#     )


#     if resp.status_code != 200:
#         abort(404)

#     # Insert into LRU
#     CACHE[cache_key] = resp.content
#     CACHE.move_to_end(cache_key)
#     CHUNKS_TO_ADD.put(cache_key)

#     # Evict if over capacity
#     if len(CACHE) > CACHE_SIZE:
#         evicted_key, _ = CACHE.popitem(last=False)
#         CHUNKS_TO_REMOVE.put(evicted_key)
        
#         print(f"Evicted LRU chunk: video {evicted_key[0]} chunk {evicted_key[1]}")

#     return Response(resp.content)




def update_controller():
    
    additions = get_chunks_to_add()
    removals = get_chunks_to_remove()
    
    if additions:
        # print(f"CDN {cdn_id} adding chunks: {additions}")
        send_update_to_controller(additions, action="add")
    if removals:
        # print(f"CDN {cdn_id} removing chunks: {removals}")
        send_update_to_controller(removals, action="rem")
    
        



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

    # Check cache
    if cache_key in CACHE:
        print(f"Cache HIT: video {video_id} chunk {chunk_id}")
        CACHE.move_to_end(cache_key)  # promote to MRU
        return CACHE[cache_key]
    
    print(f"Cache MISS: video {video_id} chunk {chunk_id}, fetching from origin...")
    
    resp = request_video(
        dst_mac_addr=ORIGIN_MAC,
        video_id=video_id,
        chunk_id=chunk_id,
        from_origin=True
    )
    
    if resp.status_code != 200:
        return bytes()
    
    data = resp.content
    CACHE[cache_key] = data
    CACHE.move_to_end(cache_key)
    CHUNKS_TO_ADD.put(cache_key)

    # Evict if over capacity
    if len(CACHE) > CACHE_SIZE:
        evicted_key, _ = CACHE.popitem(last=False)
        CHUNKS_TO_REMOVE.put(evicted_key)
        
        print(f"Evicted LRU chunk: video {evicted_key[0]} chunk {evicted_key[1]}")

    return data
    
    
def serve_chunk(video_id, chunk_id, request_pkt: Packet):
    data = fetch_chunk(video_id, chunk_id)
    if data is None:
        print(f"Origin server: video {video_id} chunk {chunk_id} not found")
        return
    


    dst_mac = request_pkt[Ether].src
    print(f"Origin server: Serving video {video_id} chunk {chunk_id} to MAC {dst_mac}") 


    send_video_response(
        dst_mac_addr=dst_mac,
        video_id=video_id,
        chunk_id=chunk_id,
        data=data,
        from_origin=False
    )
    


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="CDN Server")
    parser.add_argument("--id", type=str, required=True, help="CDN ID")
    args = parser.parse_args()

    config = json.loads(open("topo/topo.json").read())

    
    update_thread = threading.Thread(target=periodic_update, daemon=True)
    update_thread.start()
    
    try: 
        listen_for_video_requests(
            is_origin=False,
            handle_request_callback=serve_chunk
        )
    except KeyboardInterrupt:
        pass

