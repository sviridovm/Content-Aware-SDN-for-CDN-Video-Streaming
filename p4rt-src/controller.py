import argparse
from collections import deque
import contextlib
import json

import p4runtime_sh.shell as p4sh
from p4.v1 import p4runtime_pb2 as p4rt

###############################################################################
# Default parameters
###############################################################################

# Relative path of the configuration, logs, and topo directories
CFG_DIR = 'cfg'
LOGS_DIR = 'logs'

# Bridge ID and number of ports
BRIDGE_ID = 1
BRIDGE_CPU_PORT = 255

# Logs threshold
NUM_LOGS_THRESHOLD = 10

ETH_TYPE_CDN = 0x88B5  # Custom Ethertype for CDN traffic
ETH_TYPE_ARP = 0x0806  # Ethertype for ARP traffic

def mac2str(mac):
    return ':'.join('{:02x}'.format(b) for b in mac)

def ProcPacketIn(switch_name, logs_dir, num_logs_threshold):
    try:
        num_logs = 0
        while True:
            rep = p4sh.client.get_stream_packet("packet", timeout=1)
            if rep is not None:
                # Read the raw packet
                payload = rep.packet.payload
                
                 # Parse Metadata
                ingress_port_in_bytes = rep.packet.metadata[0].value
                ingress_port = int.from_bytes(ingress_port_in_bytes, "big")

                # Parse Ethernet header
                dst_mac_in_bytes = payload[0:6]
                dst_mac = mac2str(dst_mac_in_bytes)
                src_mac_in_bytes = payload[6:12]
                src_mac = mac2str(src_mac_in_bytes)
                eth_type_in_bytes = payload[12:14]
                eth_type = int.from_bytes(eth_type_in_bytes, "big")




                # rest of bytes should be raw data
                if eth_type == ETH_TYPE_CDN:
                    chunk_data = payload[17:]
                    action = payload[14:17].decode()
                    

                    num_chunks = len(chunk_data) // 8
                    for i in range(num_chunks):
                        offset = i * 8
                        video_id = int.from_bytes(chunk_data[offset:offset+4], "big")
                        chunk_id = int.from_bytes(chunk_data[offset+4:offset+8], "big")
                        cdn_port = ingress_port


                        entry = p4sh.TableEntry('MyIngress.cdn_table')
                        entry.match['video_id'] = video_id
                        entry.match['chunk_id'] = chunk_id
                        entry.action['set_cdn_port'](cdn_port)

                        if action == 'add':
                            entry.insert()
                        elif action == 'rem':
                            entry.delete()
                        else:
                            print(f"Unknown action {action} for CDN packet")



                        print("PacketIn CDN: video_id={0} chunk_id={1} cdn_port={2}".format(
                            video_id, chunk_id, cdn_port))
                    
                elif eth_type == ETH_TYPE_ARP:
                    print("PacketIn ARP?2: dst={0} src={1} port={2}".format(
                        dst_mac, src_mac, ingress_port))
                    
                    try:
                        with contextlib.redirect_stdout(None):  # A hack to suppress print statements 
                            table_entry = p4sh.TableEntry('MyIngress.bridge_table')(action='MyIngress.drop')
                            table_entry.match['hdr.ethernet.dstAddr'] = src_mac
                            table_entry.match['standard_metadata.ingress_port'] = str(ingress_port)
                            table_entry.insert()
                    except:
                        pass
                else:
                    print("PacketIn ether?: dst={0} src={1} port={2}".format(
                        dst_mac, src_mac, ingress_port))

            # Log the Ethernet address to port mapping
            num_logs += 1
            if num_logs == num_logs_threshold:
                num_logs = 0
                with open('{0}/{1}-table.json'.format(logs_dir, switch_name), 'w') as outfile:
                    with contextlib.redirect_stdout(outfile):
                        p4sh.TableEntry('MyIngress.mac_forward').read(lambda te: print(te))
                print(
                    "INFO: Log committed to {0}/{1}-table.json".format(logs_dir, switch_name))
    except KeyboardInterrupt:
        return None


###############################################################################
# Main 
###############################################################################
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Switch Script')
    parser.add_argument('--grpc-port', help='GRPC Port', required=True,
                        type=str, action="store", default='50001')
    parser.add_argument('--topo-config', help='Topology Configuration File', required=True,
                        type=str, action="store")
    
    parser.add_argument('--name', default='s1', help='Switch name', type=str)
    
    args = parser.parse_args()

    # Create a bridge name postfixed with the grpc port number
    switch_name = 'switch-{0}'.format(args.grpc_port)



    # Setup the P4Runtime connection with the bridge
    p4sh.setup(
        device_id=BRIDGE_ID, grpc_addr='127.0.0.1:{0}'.format(args.grpc_port), election_id=(0, 1),
        config=p4sh.FwdPipeConfig(
            '{0}/{1}-p4info.txt'.format(CFG_DIR, switch_name),  # Path to P4Info file
            '{0}/{1}.json'.format(CFG_DIR, switch_name)  # Path to config file
        )
    )
    
    meta = json.load(open(args.topo_config, 'r'))
    

    print("Switch Started @ Port: {0}".format(args.grpc_port))
    print("Press CTRL+C to stop ...")
    print(args.name)
    
    # install_mac_rules(meta, args.name)
    ProcPacketIn(switch_name, LOGS_DIR, NUM_LOGS_THRESHOLD)
    
    print("Switch Stopped")

    with contextlib.redirect_stdout(None):  # A hack to suppress print statements 
        # within the table_entry.match get/set objects
        # delete_static_routes(meta)
        # delete_static_routes(meta)
        pass


    # Close the P4Runtime connection
    p4sh.teardown()
