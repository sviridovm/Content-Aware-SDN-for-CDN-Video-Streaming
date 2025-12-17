
from flask import Flask, Response, abort
from collections import OrderedDict
import requests
import json

import argparse


metadata = json.loads(open("topo/topo.json").read())

cdn_hosts = metadata["hosts"]
cdn_hosts = []
cdn_hosts.append(metadata["hosts"]["h1"]["ip"].split("/")[0])
cdn_hosts.append(metadata["hosts"]["h2"]["ip"].split("/")[0])
cdn_hosts.append(metadata["hosts"]["h3"]["ip"].split("/")[0])

cdn_urls = []
for host in cdn_hosts:
    cdn_urls.append(f"http://{host}:8000")

current_cdn_index = 0

app = Flask(__name__)

#round robin load balance

@app.route("/video/<video_id>/<chunk_id>")
def serve_chunk(video_id, chunk_id):



    global current_cdn_index
    cdn_url = cdn_urls[current_cdn_index]
    
    
    print(f"Proxy: Requesting video {video_id} chunk {chunk_id} from CDN at {cdn_url}")
    
    
    current_cdn_index = (current_cdn_index + 1) % len(cdn_urls)
    origin_url = f"{cdn_url}/video/{video_id}/{chunk_id}"
    r = requests.get(origin_url)
    return str(r.content)


if __name__ == "__main__":
    
    app.run(host="0.0.0.0", port=8000)
