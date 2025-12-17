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

def install_ipv4_route(dst_ip, dst_mac, src_mac, port):
    print("bruh")
    entry = p4sh.TableEntry("ipv4_lpm")(action="ipv4_forward")
    entry.match["hdr.ipv4.dstAddr"] = str(dst_ip) + "/32"
    entry.action["dst_mac"] = dst_mac
    entry.action["src_mac"] = src_mac
    entry.action["port"] = str(port)
    
    print("Adding LPM entry:", dst_ip, "/32")

    entry.insert()

    
def delete_static_routes(meta):
    for sw in meta["switches"]:
        for host, hinfo in meta["hosts"].items():
            dst_ip = hinfo["ip"].split("/")[0]

            entry = p4sh.TableEntry("ipv4_lpm")
            entry.match["hdr.ipv4.dstAddr"] = str(dst_ip) + "/32"
            entry.delete()
            
            


def build_graph(meta):
    graph = {sw: [] for sw in meta["switches"]}

    for sw in meta["switches"]:
        for neigh in meta["ports"][sw]:
            if neigh in graph:        # neighbor is also a switch
                graph[sw].append(neigh)

    return graph


def get_output_port(meta, switch, next_hop):
    return meta["ports"][switch][next_hop]

def compute_next_hop(meta, start, target):
    graph = build_graph(meta)
    
    if start == target:
        return None  # host directly on this switch

    queue = deque([start])
    visited = {start: None}

    while queue:
        cur = queue.popleft()
        if cur == target:
            break
        for neigh in graph[cur]:
            if neigh not in visited:
                visited[neigh] = cur
                queue.append(neigh)

    # walk backward to find next-hop neighbor
    cur = target
    while visited[cur] != start:
        cur = visited[cur]
    return cur

def install_static_routes(meta):
    for sw in meta["switches"]:
        switch_mac = "aa:bb:cc:dd:ee:ff"  # becomes src mac
        print(f"Installing routes for switch {sw} with MAC {switch_mac}")
        
        for host, hinfo in meta["hosts"].items():
            dst_ip = hinfo["ip"].split("/")[0]
            dst_mac = hinfo["mac"]
            dst_switch = hinfo["switch"]

            # find next hop
            next_hop = compute_next_hop(meta, sw, dst_switch)
            if next_hop is None:
                # local host connected directly
                outport = meta["ports"][sw][host]
            else:
                outport = get_output_port(meta, sw, next_hop)

            print(f"{sw}: {dst_ip} → {outport}")
            install_ipv4_route(dst_ip, dst_mac, switch_mac, outport)

def mac_to_bytes(mac_str: str) -> bytes:
    """Convert a MAC string '00:00:00:00:00:01' to 6-byte representation."""
    return bytes(int(x, 16) for x in mac_str.split(":"))

def install_mac_forward(mac, out_port):
    entry = p4sh.TableEntry('MyIngress.mac_forward')(action='forward')
    entry.match['hdr.ethernet.dstAddr'] = mac
    entry.action['port'] = str(out_port)

    print("Adding MAC forward entry:", mac, "->", out_port)

    entry.insert()


def install_mac_table_entries(topo_metadata, sw):
    """
    Installs L2 MAC forwarding rules on all switches based on topo_metadata.
    
    p4sh: a P4Runtime switch object (StratumBmv2Switch)
    topo_metadata: dict containing 'hosts', 'switches', 'ports'
    """

    switch_ports = topo_metadata['ports'][sw]

    for host, info in topo_metadata['hosts'].items():
        host_mac = info['mac']
        host_switch = info['switch']

        if host_switch == sw:
            # host is directly connected → get the port to the host
            port = switch_ports[host]
        else:
            # host is on another switch → forward to the switch leading to that host
            # Assumes only one upstream/downstream switch per switch for simplicity
            port = None
            for neighbor, neighbor_port in switch_ports.items():
                if neighbor in topo_metadata['switches']:
                    port = neighbor_port
                    break
            if port is None:
                raise ValueError(f"Could not find port from {sw} to reach host {host}")

        # Add MAC forward entry
        print(f"Adding MAC forward entry on {sw}: {host_mac} -> port {port}")
        entry = p4sh.TableEntry('MyIngress.mac_forward')(action='forward')
        entry.match['hdr.ethernet.dstAddr'] = host_mac
        entry.action['port'] = str(port)
        entry.insert()


def install_mac_rules(metadata, switch_name):

    hosts = metadata["hosts"]
    ports = metadata["ports"][switch_name]
    
    print("Installing MAC rules for switch", switch_name)

    # Reverse map: for each host, find the port on this switch (if any)
    for host_name, host_info in hosts.items():
        mac = host_info["mac"]
        host_switch = host_info["switch"]

        if host_switch == switch_name:
            # Host is directly attached: find port by matching the hostname
            out_port = ports.get(host_name)
            if out_port is None:
                raise ValueError(f"Switch {switch_name} has no port for host {host_name}")
            
            print("to go from ", switch_name, "to host", host_name, "with mac", mac, "use port", out_port)
            install_mac_forward(mac, out_port)
        else:
            # Host is on a remote switch: forward out the inter-switch link
            # Find port that leads to that switch
            found = False
            for neighbor, p in ports.items():
                if neighbor == host_switch:
                    install_mac_forward(mac, p)
                    found = True
                    break

            if not found:
                raise ValueError(f"Switch {switch_name} has no link to {host_switch}")



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
                    table_entry = p4sh.TableEntry('MyIngress.switch_table')(action='MyIngress.forward')
                    table_entry.match['hdr.ethernet.dstAddr'] = src_mac
                    table_entry.action['port'] =  str(ingress_port)
                    table_entry.insert()
                
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
    install_mac_table_entries(meta, args.name)
    ProcPacketIn(switch_name, LOGS_DIR, NUM_LOGS_THRESHOLD)
    
    

    print("Switch Stopped")

    with contextlib.redirect_stdout(None):  # A hack to suppress print statements 
        # within the table_entry.match get/set objects
        # delete_static_routes(meta)
        # delete_static_routes(meta)
        pass


    # Close the P4Runtime connection
    p4sh.teardown()
