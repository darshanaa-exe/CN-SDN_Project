# SDN Network Delay Measurement Tool
### Mininet + Ryu OpenFlow Controller | SDN Simulation Project

> **Course:** Computer Networks (CN)
> **Project Type:** SDN Mininet-based Simulation (Orange Problem)
> **Controller:** Ryu (OpenFlow 1.3)
> **Objective:** Measure and analyze latency between hosts in a software-defined network
> **Name:** Darshana S  
> **SRN:** PES1UG24CS913

---

## Problem Statement

This project implements an **SDN-based Network Delay Measurement Tool** using Mininet and the Ryu OpenFlow controller (OpenFlow 1.3). The goal is to measure and analyze latency between hosts across paths with deliberately different link delays, observe how the SDN controller manages flow rules, and validate network behavior under both normal and failure conditions.

**Key objectives:**
- Demonstrate controller–switch interaction using OpenFlow 1.3
- Design and install explicit match–action flow rules
- Measure RTT (Round Trip Time) across multiple host pairs
- Compare latency across paths with different configured delays
- Analyze delay variation and behavior under link failure (Normal vs. Failure scenario)

---

## Topology

```
h1 ──(5ms)──┐
             s1 ──(10ms)── s2 ──(5ms)── h3
h2 ──(50ms)─┘
```

**Hosts:** h1 (`10.0.0.1`), h2 (`10.0.0.2`), h3 (`10.0.0.3`)  
**Switches:** s1, s2 (OpenFlow 1.3, OVS)  
**Link delays:**
- h1 → s1: 5ms (fast path)
- h2 → s1: 50ms (slow path)
- s1 → s2: 10ms
- s2 → h3: 5ms

**Path summary:**
- h1 → h3 (fast path): 5 + 10 + 5 = ~20ms one-way → ~40ms RTT expected
- h2 → h3 (slow path): 50 + 10 + 5 = ~65ms one-way → ~130ms RTT expected
- h1 → h2 (via s1): 5 + 50 = ~55ms one-way → ~110ms RTT expected

---

## Project Structure

```
cn-project/
├── topology.py       # Custom Mininet topology with TCLink delays
├── controller.py     # Ryu SDN controller (learning switch + optional firewall)
├── measure.py        # RTT measurement and logging utility
└── results/
    └── rtt_results.txt   # Auto-generated measurement output
```

---

## Prerequisites

- Ubuntu 20.04 / 22.04 (tested on VirtualBox VM)
- [Mininet](http://mininet.org/download/) installed
- [Ryu SDN Framework](https://ryu.readthedocs.io/en/latest/getting_started.html) installed
- Open vSwitch (OVS) — typically bundled with Mininet
- Python 3

**Install dependencies:**
```bash
sudo apt update
sudo apt install mininet python3-pip -y
pip3 install ryu
```

---

## Setup & Execution

### Step 1 — Start the Ryu Controller

Open a terminal and run:

```bash
ryu-manager controller.py
```

### Step 2 — Launch the Mininet Topology

Open a **second terminal** and run:

```bash
sudo mn --custom topology.py --topo delaytopo --controller remote --switch ovsk,protocols=OpenFlow13 --link tc
```

This starts Mininet with:
- The custom `DelayTopo` topology
- A remote Ryu controller at `127.0.0.1:6653`
- OVS switches using OpenFlow 1.3
- TC (traffic control) links to enforce per-link delay

### Step 3 — Verify Connectivity

Inside the Mininet CLI:

```
mininet> pingall
```

Expected output: **0% dropped (6/6 received)** — all hosts can reach each other.

---

## Running Measurements

### Option A — Manual ping (from Mininet CLI)

```
mininet> h1 ping -c 10 h3
mininet> h2 ping -c 10 h3
mininet> h1 ping -c 10 h2
```

### Option B — Automated RTT measurement script - (RTT logger)

Inside the Mininet CLI:

```
mininet> py __import__('sys').path.append('.')
mininet> py __import__('measure').run_all_measurements(net)
```

Results are saved to `results/rtt_results.txt` and printed as a formatted table.

### Inspect Flow Tables

```
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s1
mininet> sh ovs-ofctl -O OpenFlow13 dump-flows s2
```

---

## Test Scenarios

### Scenario 1 — Normal Operation (Delay Measurement & Path Comparison)

All links up. Ping from h1 and h2 to h3, comparing RTT across the fast and slow paths.

```
mininet> h1 ping -c 10 h3    # Fast path (~40ms RTT expected)
mininet> h2 ping -c 10 h3    # Slow path (~130ms RTT expected)
```

**Observed results:**

| Path   | Min RTT (ms) | Avg RTT (ms) | Max RTT (ms) | Mdev  | Loss |
|--------|-------------|-------------|-------------|-------|------|
| h1→h2  | 112.88      | 130.4       | 268.54      | 46.08 | 0%   |
| h1→h3  | 42.38       | 59.25       | 116.48      | 19.94 | 0%   |
| h2→h3  | 134.65      | 165.0       | 340.73      | 59.82 | 0%   |

**Analysis:** h1→h3 has the lowest RTT (~42–59ms) confirming the fast path (5+10+5ms). h2→h3 is ~3× higher (~135–165ms) reflecting the 50ms slow link on h2. The higher `mdev` on h2 paths indicates more jitter due to the higher base delay.

### Scenario 2 — Link Failure & Recovery ( Test Scenario : Normal vs. Failure)

Simulate the s1–s2 link going down and observe the effect on connectivity.

```
mininet> sh echo "===== PHASE 1: NORMAL : LINK s1-s2 UP ====="
mininet> h1 ping -c 5 -i 0.5 h3          # Baseline: packets arrive normally

mininet> sh echo "===== PHASE 2: FAILURE : LINK s1-s2 DOWN ====="
mininet> link s1 s2 down
mininet> h1 ping -c 5 -W 1 h3            # 100% packet loss expected

mininet> sh echo "===== PHASE 3: RECOVERY : LINK s1-s2 UP again ====="
mininet> link s1 s2 up
mininet> h1 ping -c 5 -i 0.5 h3          # Connectivity restored
```

**Observed behavior:**
- Phase 1 (Normal): 0% packet loss, RTT ~61–139ms
- Phase 2 (Failure): 100% packet loss, "Destination Host Unreachable"
- Phase 3 (Recovery): 0% packet loss, RTT returns to normal (~43–127ms)

### Scenario 3 — Delay Variation Under Load (iperf + concurrent ping)

Run iperf in background while measuring ping to observe delay variation under traffic load:

```
mininet> h3 iperf -s &
mininet> h2 iperf -c h3 -t 20 &
mininet> h1 ping -c 10 -i 0.5 h3
```

**Observation:** RTT jitter increases slightly when background traffic is active, demonstrating the effect of competing flows on latency.

---

## Controller Logic

The `DelayController` in `controller.py` implements:

1. **Table-miss rule** — installed on switch connect; sends unknown packets to the controller (`OFPCML_NO_BUFFER`).
2. **MAC learning** — on every `packet_in` event, the source MAC and ingress port are stored in `mac_to_port[dpid]`.
3. **Proactive forwarding rules** — once a destination MAC is known, a flow rule is installed (`priority=1`, `idle_timeout=30s`) so future packets are forwarded at line rate without controller involvement.
4. **Firewall rules (optional)** — high-priority (`priority=10`) DROP rules for specific IP pairs, installed at switch connect time with no expiry (`idle_timeout=0`).

### MAC Learning (Learning Switch)
1. Packet arrives at switch with no matching flow rule → sent to controller (packet_in event)
2. Controller records `source MAC → port` in `mac_to_port` dictionary
3. If destination MAC known → installs flow rule (priority=1, idle_timeout=30s)
4. If destination unknown → floods packet out all ports

### Flow Rule Design

| Rule | Priority | Match | Action | idle_timeout |
|------|----------|-------|--------|--------------|
| Table-miss (default) | 0 | Everything | Send to controller | 0 (permanent) |
| Learned MAC forward | 1 | dst MAC + in_port | Output specific port | 30s |
| Firewall DROP | 10 | src IP + dst IP (IPv4) | DROP (empty actions) | 0 (permanent) |

Higher priority always wins. The firewall rule (priority=10) overrides all forwarding rules when active.
- `priority=1` rules → learned MAC forwarding (auto-expire after 30s of inactivity)
- `priority=0` rule → default table-miss, unknown packets sent to Ryu controller


---


## Expected Output

**Mininet startup:**
```
*** Creating network
*** Adding hosts: h1 h2 h3
*** Adding switches: s1 s2
*** Adding links: (5ms delay)(5ms delay)(50ms delay)(50ms delay)(10ms delay)(10ms delay)(5ms delay)(5ms delay)
*** Starting CLI
```

**RTT summary (from measure.py):**
```
===== CLEAN RTT SUMMARY =====
Path       Min RTT      Avg RTT      Max RTT      Mdev         Loss %
-----------------------------------------------------------------------
h1->h2     112.88       130.4        268.54       46.08        0
h1->h3     42.38        59.25        116.48       19.94        0
h2->h3     134.65       165.0        340.73       59.82        0
```

**Flow table (s1) after learning:**
```
priority=1,in_port="s1-eth2",dl_dst=<MAC> actions=output:"s1-eth1"
priority=1,in_port="s1-eth1",dl_dst=<MAC> actions=output:"s1-eth2"
priority=0 actions=CONTROLLER:65535
```

---

## Proof of Execution Screenshots

| Screenshot | Description |
|---|---|
| `01-delay_measurement1.png` | Mininet startup + pingall + h1→h3 ping |
| `02-delay_measurement2.png` | h2→h3 ping + flow table dump + link failure test |
| `03-using_ping_for_delay_measurement.png` | Manual ping across all 3 host pairs |
| `04-recort_RTT_values.png` | 20-packet extended ping for RTT recording |
| `05-compare_across_paths.png` | Side-by-side path comparison (h1→h3 vs h2→h3) |
| `06-analyze_delay_variation.png` | Delay variation under iperf background load |
| `07-normal_vs_failure.png` | Full normal → failure → recovery scenario |
| `log_file1.png` | measure.py automated RTT output in Mininet CLI |
| `log_file2.png` | rtt_results.txt content after saving |

---

## References

1. Mininet Documentation — http://mininet.org/
2. Ryu SDN Framework Documentation — https://ryu.readthedocs.io/
3. OpenFlow 1.3 Specification — https://opennetworking.org/wp-content/uploads/2014/10/openflow-spec-v1.3.0.pdf
4. Open vSwitch Documentation — https://docs.openvswitch.org/
5. Ryu `simple_switch_13.py` reference implementation — https://github.com/faucetsdn/ryu/blob/master/ryu/app/simple_switch_13.py
