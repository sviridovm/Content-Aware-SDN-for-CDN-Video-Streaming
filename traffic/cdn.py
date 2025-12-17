from curses import raw
from typing import List
from flask import Flask, Response, abort
from collections import OrderedDict
import requests


from scapy.all import Ether, bind_layers, sendp, Raw
from scapy.fields import IntField, ShortField 
from scapy.packet import Packet

import argparse
import threading
import queue


app = Flask(__name__)

ORIGIN_URL = "http://10.0.0.1:8000/video"     # now /video/<vid>/<chunk>
CACHE_SIZE = 100                               # number of chunks
CACHE = OrderedDict()                          # (video_id, chunk_id) -> bytes

CHUNKS_TO_ADD = queue.Queue()
CHUNKS_TO_REMOVE = queue.Queue()


@app.route("/video/<video_id>/<chunk_id>")
def serve_chunk(video_id, chunk_id):
    cache_key = (video_id, chunk_id)

    # Check cache
    if cache_key in CACHE:
        print(f"Cache HIT: video {video_id} chunk {chunk_id}")
        CACHE.move_to_end(cache_key)  # promote to MRU
        return Response(CACHE[cache_key], mimetype="video/mp4")

    print(f"Cache MISS: video {video_id} chunk {chunk_id}, fetching from origin...")

    # Fetch from origin: /video/<vid>/<chunk>
    origin_url = f"{ORIGIN_URL}/{video_id}/{chunk_id}"
    r = requests.get(origin_url)

    if r.status_code != 200:
        abort(404)

    # Insert into LRU
    CACHE[cache_key] = r.content
    CACHE.move_to_end(cache_key)
    CHUNKS_TO_ADD.put(cache_key)

    # Evict if over capacity
    if len(CACHE) > CACHE_SIZE:
        evicted_key, _ = CACHE.popitem(last=False)
        CHUNKS_TO_REMOVE.put(evicted_key)
        
        print(f"Evicted LRU chunk: video {evicted_key[0]} chunk {evicted_key[1]}")

    return Response(r.content, mimetype="video/mp4")





ETH_TYPE_CDN = 0x88B5


class CDNHeader(Packet):
    name = "CDNHeader"
    fields_desc = [
        IntField("cdn_id", 0),
    ]

bind_layers(Ether, CDNHeader, type=ETH_TYPE_CDN)



from itertools import islice
def update_controller(cdn_id: int):
    
    additions = get_chunks_to_add()
    removals = get_chunks_to_remove()
    
    if additions:
        print(f"CDN {cdn_id} adding chunks: {additions}")
        send_update(cdn_id, additions, action="add")
    if removals:
        print(f"CDN {cdn_id} removing chunks: {removals}")
        send_update(cdn_id, removals, action="rem")
    
        
def send_update(cdn_id: int, chunk_list: list, action: str):
    eth = Ether(dst="ff:ff:ff:ff:ff:ff", type=ETH_TYPE_CDN)
    cdn_header = CDNHeader(cdn_id=cdn_id)
    packet = eth / cdn_header
    
    
    chunks_per_packet = 10
    
    islice_iter = iter(chunk_list)
    for _ in range(0, len(chunk_list), chunks_per_packet):
        chunk_subset = list(islice(islice_iter, chunks_per_packet))
        chunk_ids_bytes = f'{action}'.encode() 
        for video_id, chunk_id in chunk_subset:
            chunk_ids_bytes += video_id.to_bytes(4, byteorder='big') + chunk_id.to_bytes(4, byteorder='big')
        
        
        packet_with_chunks = packet / chunk_ids_bytes
        sendp(packet_with_chunks, iface="eth0", verbose=False)


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
    
    
def periodic_update(cdn_id: int):
    while True:
        try:
            update_controller(cdn_id)
            threading.Event().wait(1) 
        except KeyboardInterrupt:
            return

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="CDN Server")
    parser.add_argument("--id", type=int, required=True, help="CDN ID")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()

    
    update_thread = threading.Thread(target=periodic_update, args=(args.id,), daemon=True)
    update_thread.start()
    
    app.run(host="0.0.0.0", port=args.port)
