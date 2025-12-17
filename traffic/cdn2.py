import json
import socket
from flask import Response, abort
from collections import OrderedDict


from scapy.all import Ether, bind_layers, sendp, Raw
from scapy.fields import IntField, ShortField 
from scapy.packet import Packet

import argparse
import threading
import queue

from traffic.util import ETH_TYPE_MSG_TO_CONTROLLER


metadata = json.load(open("topo/topo.json"))

ORIGIN_MAC = metadata["hosts"]["h0"]["mac"]
ORIGIN_IP = metadata["hosts"]["h0"]["ip"]



CACHE_SIZE = 100                               # number of chunks
CACHE = OrderedDict()                          # (video_id, chunk_id) -> bytes

CHUNKS_TO_ADD = queue.Queue()
CHUNKS_TO_REMOVE = queue.Queue()


def serve_chunk(video_id, chunk_id) -> Response:
    cache_key = (video_id, chunk_id)

    # Check cache
    if cache_key in CACHE:
        print(f"Cache HIT: video {video_id} chunk {chunk_id}")
        CACHE.move_to_end(cache_key)  # promote to MRU
        return Response(CACHE[cache_key], mimetype="video/mp4")

    print(f"Cache MISS: video {video_id} chunk {chunk_id}, fetching from origin...")

    



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

    return Response(r.content)




from itertools import islice
def update_controller():
    
    additions = get_chunks_to_add()
    removals = get_chunks_to_remove()
    
    if additions:
        # print(f"CDN {cdn_id} adding chunks: {additions}")
        send_update(additions, action="add")
    if removals:
        # print(f"CDN {cdn_id} removing chunks: {removals}")
        send_update(removals, action="rem")
    
        
def send_update(chunk_list: list, action: str):
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
    
    
def periodic_update():
    while True:
        try:
            update_controller()
            threading.Event().wait(1) 
        except KeyboardInterrupt:
            return





if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="CDN Server")
    parser.add_argument("--id", type=str, required=True, help="CDN ID")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()

    config = json.loads(open("topo/topo.json").read())

    # ip = config["hosts"][args.id]["ip"]
    
    
    update_thread = threading.Thread(target=periodic_update, daemon=True)
    update_thread.start()
    
    
    # socket server
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", args.port))
    print(f"Socket server listening on port {args.port}")
    while True:
        server_socket.listen(5)
        try:
            client_socket, addr = server_socket.accept()
            print(f"Accepted connection from {addr}")
            data = b''
            
            data = client_socket.recv(8)  # read first 8 bytes (CDN header)
            video_id = int.from_bytes(data[0:4], "big")
            chunk_id = int.from_bytes(data[4:8], "big")
            
            print(f"Received {len(data)} bytes from client")
            
            

            chunk_data = serve_chunk(video_id, chunk_id).data
            
            
            
            client_socket.sendall(chunk_data)
            
            client_socket.close()
            
            # parse HTTP request
            # http_request = data[8:]  # skip first 8 bytes (CDN header)
            # response = requests.get(f"http://
        except KeyboardInterrupt:
            break

    
    # app.run(host="0.0.0.0", port=args.port)
