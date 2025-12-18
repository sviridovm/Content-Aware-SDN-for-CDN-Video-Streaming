import json

import argparse
from util import request_video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=str, required=True, help="hostID")
    topo_config = json.loads(open("topo/topo.json").read())
    args = parser.parse_args()
    
    my_mac = topo_config["hosts"][f"{args.id}"]["mac"]
    print(f"My MAC address: {my_mac}")


    while True:
        try:
            video_id, chunk_id = map(int, input("Enter video and chunk ID:, separated by space: ").split())
            print(f"fetching {video_id} {chunk_id}")
            
            resp = request_video(
                dst_mac_addr="FF:FF:FF:FF:FF:FF",
                src_mac_addr=my_mac,
                video_id=video_id,
                chunk_id=chunk_id,
                from_origin=False,
                host=f"{args.id}"
            )

            if resp is not None:
                print("fetched:", resp)
            else:
                print("no response received.")


        except KeyboardInterrupt:
            break

    
    print("end")
        
if __name__ == "__main__":
    main()
