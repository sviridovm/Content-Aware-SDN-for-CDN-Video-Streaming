# origin_server.py
from collections import OrderedDict
import queue
from flask import Flask, Response, send_file, abort
import os

import requests

app = Flask(__name__)
VIDEO_DIR = "./video"
CACHE_SIZE = 100                               # number of chunks
CACHE = OrderedDict()                          # (video_id, chunk_id) -> bytes

CHUNKS_TO_ADD = queue.Queue()
CHUNKS_TO_REMOVE = queue.Queue()

import json
metadata = json.load(open("topo/topo.json"))

IP = metadata["hosts"]["origin"]["ip"]

ORIGIN_URL = f"http://{IP}:8000/video"     # now /video/<vid>/<chunk>


@app.route("/video/<video_id>/<chunk_id>")
def serve_chunk(video_id, chunk_id):
    cache_key = (video_id, chunk_id)

    # Check cache
    if cache_key in CACHE:
        print(f"Cache HIT: video {video_id} chunk {chunk_id}")
        CACHE.move_to_end(cache_key)  # promote to MRU
        return str(CACHE[cache_key].content)

    print(f"Cache MISS: video {video_id} chunk {chunk_id}, fetching from origin... at {ORIGIN_URL}")

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


    
    # return requests.Response(r.content, mimetype="video/mp4")
    # return requests.Response(r.content)
    return str(r.content)
    



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
