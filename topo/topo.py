#!/usr/bin/env python3
from curses import meta
import json
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.util import macColonHex
from stratum import StratumBmv2Switch

from collections import deque


class CDNTopo(Topo):

    def build(self):
        
        # Core and edge switches
        core = self.addSwitch('s1', cls=StratumBmv2Switch)
        edge = self.addSwitch('s2', cls=StratumBmv2Switch)
        # edge2 = self.addSwitch('s3', cls=StratumBmv2Switch)

        # # Hosts: origin, caches, clients
        # origin = self.addHost('h0', ip='10.0.0.1/24', mac=macColonHex(0))
        # cache1 = self.addHost('h1', ip='10.0.0.2/24', mac=macColonHex(1))
        # cache2 = self.addHost('h2', ip='10.0.0.3/24', mac=macColonHex(2))
        # cache3 = self.addHost('h3', ip='10.0.0.4/24', mac=macColonHex(3))

        # client1 = self.addHost('h4', ip='10.0.0.5/24', mac=macColonHex(4))
        # client2 = self.addHost('h5', ip='10.0.0.6/24', mac=macColonHex(5))
        # client3 = self.addHost('h6', ip='10.0.0.7/24', mac=macColonHex(6))
        
        
        origin = self.addHost('h0', )
        cache1 = self.addHost('h1',  )
        cache2 = self.addHost('h2',  )
        cache3 = self.addHost('h3',  )

        client1 = self.addHost('h4',  )
        client2 = self.addHost('h5',  )
        client3 = self.addHost('h6', )
        
        proxy = self.addHost('proxy', )

        # Core <--> Edge link
        self.addLink(core, edge, port1=1, port2=1)

        # Core <--> Origin
        self.addLink(core, origin, port1=2, port2=1)

        # Edge <--> Caches
        self.addLink(edge, cache1, port1=2, port2=1)
        self.addLink(edge, cache2, port1=3, port2=1)
        self.addLink(edge, cache3, port1=4, port2=1)

        # Edge <--> Clients
        self.addLink(edge, client1, port1=5, port2=1)
        self.addLink(edge, client2, port1=6, port2=1)
        self.addLink(edge, client3, port1=7, port2=1)
        
        self.addLink(edge, proxy, port1=8, port2=1)
        
        self.topo_data = None
        self.graph = None

    def get_topology_metadata(self):
        """
        Returns a dictionary containing:
            - hosts and their IP/MAC
            - switches
            - port mappings: switch_name -> { neighbor_name: port_no }
        """
        
        if self.topo_data is not None:
            return self.topo_data
        
        
        topo_data = {
            "hosts": {},
            "switches": [],
            "ports": {},      # switch_name -> { neighbor -> port_num }
        }

        # record switches
        topo_data["switches"] = self.switches()

        # record hosts
        for h in self.hosts():
            topo_data["hosts"][h] = {
                # "ip": self.nodeInfo(h)["ip"],
                "ip": None,
                # "mac": self.nodeInfo(h)["mac"],
                "mac": "",
                "switch": None,    # filled in below
            }

        # create empty port maps
        for sw in self.switches():
            topo_data["ports"][sw] = {}

        # iterate links to get port numbers
        
        
        for n1, n2, link in self.links(sort=True, withInfo=True):
            
            # print(n1, n2, link)
            
            intf1 = link['port1']
            intf2 = link['port2']

            if n1 in topo_data["switches"]:
                topo_data["ports"][n1][n2] = intf1
            if n2 in topo_data["switches"]:
                topo_data["ports"][n2][n1] = intf2

            # map hosts to their switches
            if n1 in topo_data["hosts"] and n2 in topo_data["switches"]:
                topo_data["hosts"][n1]["switch"] = n2
            if n2 in topo_data["hosts"] and n1 in topo_data["switches"]:
                topo_data["hosts"][n2]["switch"] = n1

        self.topo_data = topo_data
        return topo_data
        

if __name__ == '__main__':
    topo = CDNTopo()
    
    metadata = topo.get_topology_metadata()
    
    
    
    net = Mininet(topo=topo, controller=None, switch=StratumBmv2Switch)
    net.start()
    


    
    print("*** Network started")
    try:
        
        for h_name in topo.hosts():
            host = net.get(h_name)
            # print mac and ip
            print(f"Host {h_name}: IP={host.IP()} MAC={host.MAC()}")


        for host_name in topo.hosts():
            host = net.get(host_name)
            host_mac = host.MAC()
            metadata["hosts"][host_name]["mac"] = host_mac
            metadata["hosts"][host_name]["ip"] = host.IP()

        json.dump(metadata, open("topo/topo.json", "w"), indent=4)


        CLI(net)
        

    finally:
        net.stop()
