import json
import requests

import socket
import argparse
from http.server import BaseHTTPRequestHandler
from io import BytesIO

from traffic.util import request_video

# CDN_HOSTS = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
# SERVER_IP = CDN_HOSTS[0] 

# SERVER_IP = topo_config["hosts"]["h1"]["ip"].split("/")[0]

# SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}"

# class HTTPRequest(BaseHTTPRequestHandler):
#     def __init__(self, request_text):
#         self.rfile = BytesIO(request_text)
#         self.raw_requestline = self.rfile.readline()
#         self.error_code = self.error_message = None
#         self.parse_request()
        
# def parse_http_response(data: bytes) -> HTTPRequest:
#     req = HTTPRequest(data)
#     if req.error_code:
#         raise ValueError(f"Invalid HTTP request {req.error_code}")
#     return req

# class CDNConnection():
#     def __init__(self, server_ip = SERVER_IP, server_port: int = SERVER_PORT):
#         self.server_ip = server_ip
#         self.server_port = server_port

        

#     def get_chunk(self, video_id: int, chunk_id: int) -> bytes:
        
#         # open TCP connection to server, send HTTP requests with CDN headers prepended
#         self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.tcp_sock.connect((self.server_ip, self.server_port))

#         # construct CDN header
#         cdn_header = video_id.to_bytes(4, byteorder='big') + chunk_id.to_bytes(4, byteorder='big')
        
        
#         self.tcp_sock.sendall(cdn_header)
        
#         # wait for response
#         response = b''
#         while True:
#             data = self.tcp_sock.recv(4096)
#             if not data:
#                 break
#             response += data
            
            
#         print("Closing TCP socket, received ", len(response), "bytes")

#         self.tcp_sock.close()
#         http_response = parse_http_response(response)
        
#         print(f"Received HTTP response: {http_response.command} {http_response.path} {http_response.request_version}")
        
#         return http_response.rfile.read()           
            
    






def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-id", type=int, required=False, help="hostID")
    # topo_config = json.loads(open("topo/topo.json").read())

    while True:
        try:
            video_id, chunk_id = map(int, input("Enter video and chunk ID:, separated by space: ").split())
            print(f"fetching {video_id} {chunk_id}")
            
            resp = request_video(
                dst_mac_addr="FF:FF:FF:FF:FF:FF",
                video_id=video_id,
                chunk_id=chunk_id,
                from_origin=False
            )

            print("fetched:", resp.content)


        except KeyboardInterrupt:
            break

    
    print("end")
        
if __name__ == "__main__":
    main()
