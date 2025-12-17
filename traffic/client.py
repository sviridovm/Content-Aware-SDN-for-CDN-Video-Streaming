import requests

from scapy.all import Ether, IP, TCP, bind_layers, sendp, sniff, Raw
from scapy.fields import IntField, ShortField 
from scapy.packet import Packet
import argparse

from uuid import getnode as get_mac

ETH_TYPE_CDN = 0x88B5
SERVER = "http://10.0.0.2:9000"
SERVER_PORT = 9000
SERVER_IP = "10.0.0.2"



class CDNHeader(Packet):
    name = "CDNHeader"
    fields_desc = [
        IntField("video_id", 0),
        IntField("chunk_id", 0),
    ]


bind_layers(IP, TCP)
bind_layers(TCP, CDNHeader, dport=SERVER_PORT)


class CDNConnection():
    def __init__(self, dest_mac: str, iface: str = "eth0"):
        self.dest_mac = dest_mac
        self.iface = iface
        self.src_mac = get_mac()

    def _send_cdn_packet(self, video_id, chunk_id, payload):
        
        eth = Ether(dst=self.dest_mac, type=ETH_TYPE_CDN)
        cdn_header = CDNHeader(video_id=video_id, chunk_id=chunk_id)
        ip_layer = IP(dst=SERVER_IP)
        tcp_layer = TCP(dport=SERVER_PORT, sport=12345)
        packet = eth / cdn_header / ip_layer / tcp_layer / payload


        sendp(packet, iface=self.iface, verbose=False)
         

    def get_chunk(self, video_id: int, chunk_id: int) -> bytes:

        url = f"{SERVER}/{video_id}/{chunk_id}"

        http_body = requests.Request('GET', url).prepare().body


        self._send_cdn_packet(
            video_id=video_id,
            chunk_id=chunk_id,
            payload=http_body if http_body else b'',
        )

        # listen for response packet
        
        def match_reply(pkt):
            return (
                CDNHeader in pkt
                and pkt[CDNHeader].video_id == video_id
                and pkt[CDNHeader].chunk_id == chunk_id
                and Raw in pkt  # must contain payload
            )

        resp = sniff(
            lfilter=match_reply,
            iface=self.iface,
            timeout=3,
        )

        if not resp:
            print("[client] ERROR: No reply received")
            return b""

        tcp_payloads = []
        for pkt in resp:
            if Raw in pkt:
                seq = pkt[TCP].seq
                data = bytes(pkt[Raw].load)
                tcp_payloads.append((seq, data))

        # sort them in stream order
        tcp_payloads.sort(key=lambda x: x[0])
        payload = b"".join([data for _, data in tcp_payloads])



        print(f"[client] Received {len(payload)} bytes")

        
        header_bytes, body_bytes = payload.split(b"\r\n\r\n", 1)
    
        header_text = header_bytes.decode("iso-8859-1")  # safe for HTTP headers
        print(header_text)

        
        return body_bytes
        
        

        # if resp.status_code == 200:
        #     print(f"[client] Received {len(resp.content)} bytes")
        # else:
        #     print("[client] Error:", resp.text)
         
            
    






def main():
    # parse out CDN MAC address (this would be given my a view service, but hardcoded here for simplicity)
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdn-mac", type=str, required=True, help="CDN MAC address")
    args = parser.parse_args()

    cdn = CDNConnection(dest_mac=args.cdn_mac)
    
    
    while True:
        video_id, chunk_id = map(int, input("Enter video and chunk ID:, separated by space: ").split())
        if chunk_id and video_id == 0:
            break

        cdn.get_chunk(video_id, chunk_id)
        
        
if __name__ == "__main__":
    main()
