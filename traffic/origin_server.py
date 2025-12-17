# origin_server.py
from flask import Flask, send_file, abort
import os

app = Flask(__name__)
VIDEO_DIR = "/workdir/video"

@app.route("/video/<video_id>/<chunk_id>")
def serve_chunk(video_id, chunk_id):
    
    print(f"Origin server: Serving video {video_id} chunk {chunk_id}")
    
    path = os.path.join(VIDEO_DIR, f"{video_id}/{chunk_id}.bin")
    if not os.path.exists(path):
        print(f"Origin server: video {video_id} chunk {chunk_id} not found")
        print("path is ", path)
        
        abort(404)
    # return send_file(path, mimetype="video/mp4")
    
    
    print(f"Origin server: Serving video {video_id} chunk {chunk_id}")
    return send_file(path)

if __name__ == "__main__":
    
    app.run(host="0.0.0.0", port=8000)
