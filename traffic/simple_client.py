import json
import os
import requests

topo_config = json.loads(open("topo/topo.json").read())

SERVER_IP = topo_config["hosts"]["proxy"]["ip"].split("/")[0]
SERVER_PORT = 8000
    
SERVER = f"http://{SERVER_IP}:{SERVER_PORT}"

def get_chunk(video_id: int, chunk_id: int):

    url = f"{SERVER}/video/{video_id}/{chunk_id}"

    resp = requests.get(url)


    
    os.makedirs("downloads", exist_ok=True)
    # write to downloads/file.txt
    with open("downloads/file.txt", "wb") as f:
        f.write(resp.content)

    if resp.status_code == 200:
        print(resp.text)

    else:
        print("[client] Error:", resp.text)

def main():
    # parse out CDN MAC address (this would be given my a view service, but hardcoded here for simplicity)
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--cdn-mac", type=str, required=True, help="CDN MAC address")
    # args = parser.parse_args()
    # global src_mac
    # src_mac = args.src_mac
    
    
     while True:
        try:
            video_id, chunk_id = map(int, input("Enter video and chunk ID:, separated by space: ").split())
            print(f"fetching {video_id} {chunk_id}")
            
            
            get_chunk(video_id, chunk_id)
            
        except KeyboardInterrupt:
            break

    
        
        
if __name__ == "__main__":
    main()
