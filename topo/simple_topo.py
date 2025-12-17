#!/usr/bin/env python3
from curses import meta
import json
from mininet.topo import Topo
from mininet.net import Mininet
# from mininet.node import Controller, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.util import macColonHex

from mininet.node import OVSSwitch
# from mininet.

from collections import deque


class CDNTopo(Topo):

    def build(self):
        
        # Core and edge switches
        core = self.addSwitch('s1',)
        
        
        middle = self.addSwitch('s3',)
        
        edge = self.addSwitch('s2',)

        
        
        origin = self.addHost('h0', )
        cache1 = self.addHost('h1',  )
        cache2 = self.addHost('h2',  )
        cache3 = self.addHost('h3',  )

        client1 = self.addHost('h4',  )
        client2 = self.addHost('h5',  )
        client3 = self.addHost('h6', )

        proxy = self.addHost('proxy', )


        # Core <--> Origin
        self.addLink(core, origin)

        self.addLink(core, middle)
        self.addLink(middle, proxy)
        self.addLink(edge, proxy)

        # Middle <--> Caches
        self.addLink(middle, cache1)
        self.addLink(middle, cache2)
        self.addLink(middle, cache3)
        
        self.addLink(middle, edge)
        
        # Edge <--> Clients
        self.addLink(edge, client1)
        self.addLink(edge, client2)
        self.addLink(edge, client3)
        
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
        

    
    
    

   

    

    
    def get_switch_mac(self, switch):
        # return self.nodeInfo(switch)["params"]["mac"]
        pass
        # mac is defined by mininet
    
class MyTopo( Topo ):
    "Simple topology example."

    def build( self ):
        "Create custom topo."

        # Add hosts and switches
        leftHost = self.addHost( 'h1' )
        rightHost = self.addHost( 'h2' )
        leftSwitch = self.addSwitch( 's3' )
        rightSwitch = self.addSwitch( 's4' )

        # Add links
        self.addLink( leftHost, leftSwitch )
        self.addLink( leftSwitch, rightSwitch )
        self.addLink( rightSwitch, rightHost )

if __name__ == '__main__':
    topo = CDNTopo()
    
    metadata = topo.get_topology_metadata()
    
    net = Mininet(topo=topo, switch=OVSSwitch)
    net.start()
    
    
    for host_name in topo.hosts():
            host = net.get(host_name)
            host_mac = host.MAC()
            metadata["hosts"][host_name]["mac"] = host_mac
            metadata["hosts"][host_name]["ip"] = host.IP()

    json.dump(metadata, open("topo/topo.json", "w"), indent=4)

    
    print("*** Network started")
    try:
        CLI(net)
        

    finally:
        net.stop()
