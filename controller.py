# Import Ryu libraries
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4

class DelayController(app_manager.RyuApp):
    # Use OpenFlow version 1.3
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # --- FIREWALL RULES ---
    # Block traffic FROM h2 (10.0.0.2) TO h3 (10.0.0.3)
    # To disable blocking, set ENABLE_FIREWALL = False
    ENABLE_FIREWALL = False
    BLOCKED_SRC_IP = '10.0.0.2'
    BLOCKED_DST_IP = '10.0.0.3'

    def __init__(self, *args, **kwargs):
        super(DelayController, self).__init__(*args, **kwargs)
        # This table remembers which MAC address is on which port
        self.mac_to_port = {}

    # This runs once when a switch connects to the controller
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Default rule: if controller doesn't know where to send, flood
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        # --- SCENARIO 2: FIREWALL RULE ---
        # Install a DROP rule for h2 -> h3 traffic (higher priority than default)
        if self.ENABLE_FIREWALL:
            self.logger.info(
                "[FIREWALL] Switch %s: Installing block rule %s -> %s",
                datapath.id, self.BLOCKED_SRC_IP, self.BLOCKED_DST_IP
            )
            # Block h2 -> h3 (drop packets matching this IP pair)
            block_match = parser.OFPMatch(
                eth_type=0x0800,           # IPv4
                ipv4_src=self.BLOCKED_SRC_IP,
                ipv4_dst=self.BLOCKED_DST_IP
            )
            # Empty actions list = DROP
            self.add_flow(datapath, priority=10, match=block_match, actions=[])

            # Also block reverse direction: h3 -> h2
            block_match_reverse = parser.OFPMatch(
                eth_type=0x0800,
                ipv4_src=self.BLOCKED_DST_IP,
                ipv4_dst=self.BLOCKED_SRC_IP
            )
            self.add_flow(datapath, priority=10, match=block_match_reverse, actions=[])

    # Helper function to install a flow rule into a switch
    # idle_timeout=0 means the rule never expires (used for permanent rules like firewall drops)
    # idle_timeout=N means the rule is removed after N seconds of inactivity (used for learned MAC rules)
    def add_flow(self, datapath, priority, match, actions, idle_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(
                    ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst,
                                idle_timeout=idle_timeout)
        datapath.send_msg(mod)

    # This runs every time a packet arrives that the switch doesn't know how to handle
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        dst = eth.dst  # destination MAC
        src = eth.src  # source MAC
        dpid = datapath.id  # switch ID

        self.mac_to_port.setdefault(dpid, {})

        # Learn: remember which port this source MAC came from
        self.mac_to_port[dpid][src] = in_port
        self.logger.info("Packet in switch=%s src=%s dst=%s port=%s",
                         dpid, src, dst, in_port)

        # If we know where destination is, send there. Otherwise flood.
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # If we know the destination, install a flow rule so future packets
        # don't need to come to the controller.
        # idle_timeout=30: rule expires after 30s of inactivity (good practice for learned MAC rules)
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.add_flow(datapath, 1, match, actions, idle_timeout=30)

        # Send this current packet out
        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=msg.buffer_id,
                                  in_port=in_port,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)
