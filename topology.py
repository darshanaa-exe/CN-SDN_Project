from mininet.topo import Topo
from mininet.link import TCLink

class DelayTopo(Topo):
    def build(self):
        # Add 3 hosts (like computers)
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        # Add 2 switches (like routers)
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        # Connect hosts to switches WITH specific delays
        # Path A: h1 -> s1 -> s2 -> h3  (fast path, low delay)
        self.addLink(h1, s1, delay='5ms')
        self.addLink(s1, s2, delay='10ms')
        self.addLink(s2, h3, delay='5ms')

        # Path B: h2 -> s1 (slower link)
        self.addLink(h2, s1, delay='50ms')

# This line is required by Mininet to find the topology
topos = {'delaytopo': (lambda: DelayTopo())}
