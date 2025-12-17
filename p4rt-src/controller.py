############################################################################
##
##     This file is part of Purdue CS 536.
##
##     Purdue CS 536 is free software: you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation, either version 3 of the License, or
##     (at your option) any later version.
##
##     Purdue CS 536 is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.
##
##     You should have received a copy of the GNU General Public License
##     along with Purdue CS 536. If not, see <https://www.gnu.org/licenses/>.
##
#############################################################################

import json
import argparse
import contextlib
from random import random
from typing import List, Tuple

import pydantic
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

# Ethernet type values (https://en.wikipedia.org/wiki/EtherType)
ETH_TYPE_ARP = 0x0806
ETH_TYPE_VLAN = 0x8100
ETH_TYPE_CDN = 0x88B5  # Custom Ethertype for CDN traffic
ETH_TYPE_ipv4 = 0x0800

CHUNK_MAP = {}  # (video_id, chunk_id) -> CDN server port
NUM_CDNS = 3  # Number of CDN servers



class CDNMessage(pydantic.BaseModel):
    cdn_id: int
    chunks: List[Tuple[int, int]]  # List of (video_id, chunk_id)
    

### Function that listens to CDN messages and installs routing rules accordingly
def listen_to_cdn_messages():
    pass


###############################################################################
# Multicast group functions
###############################################################################

# Create a multicast group entry
# def InstallMcastGrpEntry(mcast_group_id, bridge_ports):
#     mcast_entry = p4sh.MulticastGroupEntry(mcast_group_id)
#     for port in bridge_ports:
#         mcast_entry.add(port)
#     mcast_entry.insert()

# Delete a multicast group entry
# def DeleteMcastGrpEntry(mcast_group_id):
#     mcast_entry = p4sh.MulticastGroupEntry(mcast_group_id)
#     mcast_entry.delete()

###############################################################################
# Helper functions
###############################################################################

# MAC address in bytes to string
def mac2str(mac):
    return ':'.join('{:02x}'.format(b) for b in mac)

# Install multicast group entry


###############################################################################
# Packet processing functions
###############################################################################

# Process incoming packets
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


                if eth_type == ETH_TYPE_CDN:
                    chunk_data = payload[17:]
                    # action = payload[14:17].decode()
                    
                    num_chunks = len(chunk_data) // 8
                    for i in range(num_chunks):
                        offset = i * 8
                        video_id = int.from_bytes(chunk_data[offset:offset+4], "big")
                        chunk_id = int.from_bytes(chunk_data[offset+4:offset+8], "big")
                        cdn_port = ingress_port
                        CHUNK_MAP[(video_id, chunk_id)] = cdn_port
                        print("PacketIn CDN: video_id={0} chunk_id={1} cdn_port={2}".format(
                            video_id, chunk_id, cdn_port))
                    
                    
                else:
                    print("PacketIn ether?: dst={0} src={1} port={2}".format(
                        dst_mac, src_mac, ingress_port))

            # Log the Ethernet address to port mapping
            num_logs += 1
            if num_logs == num_logs_threshold:
                num_logs = 0
                with open('{0}/{1}-table.json'.format(logs_dir, switch_name), 'w') as outfile:
                    with contextlib.redirect_stdout(outfile):
                        p4sh.TableEntry('MyIngress.switch_table').read(lambda te: print(te))
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
    args = parser.parse_args()

    # Create a bridge name postfixed with the grpc port number
    switch_name = 'switch-{0}'.format(args.grpc_port)

    # Get Multicast/VLAN ID to ports mapping
    # with open(args.topo_config, 'r') as infile:
        # topo_config = json.loads(infile.read())


    # Setup the P4Runtime connection with the bridge
    p4sh.setup(
        device_id=BRIDGE_ID, grpc_addr='127.0.0.1:{0}'.format(args.grpc_port), election_id=(0, 1),
        config=p4sh.FwdPipeConfig(
            '{0}/{1}-p4info.txt'.format(CFG_DIR, switch_name),  # Path to P4Info file
            '{0}/{1}.json'.format(CFG_DIR, switch_name)  # Path to config file
        )
    )

    print("Switch Started @ Port: {0}".format(args.grpc_port))
    print("Press CTRL+C to stop ...")


    mcast_group_id = topo_config['switch'][args.grpc_port]['mcast']['id']
    mcast_group_ports = topo_config['switch'][args.grpc_port]['mcast']['ports']

    # Install broadcast rule
    # InstallMcastGrpEntry(mcast_group_id, mcast_group_ports + [BRIDGE_CPU_PORT])

    # Install VLAN rules
    with contextlib.redirect_stdout(None):  # A hack to suppress print statements 
        # within the table_entry.match get/set objects
        pass

    with open('{0}/{1}-vlan-table.json'.format(LOGS_DIR, switch_name), 'w') as outfile:
        with contextlib.redirect_stdout(outfile):
            p4sh.TableEntry('MyEgress.vlan_table').read(lambda te: print(te))
        print("INFO: Log committed to {0}/{1}-vlan-table.json".format(LOGS_DIR, switch_name))

    # Start the packet-processing loop
    ProcPacketIn(switch_name, LOGS_DIR, NUM_LOGS_THRESHOLD)

    print("Switch Stopped")

    # Delete broadcast rule
    # DeleteMcastGrpEntry(mcast_group_id)

    with contextlib.redirect_stdout(None):  # A hack to suppress print statements 
        # within the table_entry.match get/set objects
        
        #TODO: install ipv4 routing rules here
        # should have different rules for edge and core switches
        
        
        
        
        pass







    # Close the P4Runtime connection
    p4sh.teardown()
