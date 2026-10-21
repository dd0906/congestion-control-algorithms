#!/usr/bin/env python3
"""Fast-path QACK proxy — replaces the P4/BMv2 data-plane design in
scripts/qack.p4 with a plain Scapy raw-socket implementation, run inside the
'switch' network namespace, sniffing/injecting on its sender-facing interface
(sw-se). Adopted under a hard 1-hour project deadline that made a from-source
BMv2/p4c build infeasible — see docs/OBSERVATIONS.md item 9. Implements the
same *logic* as qack.p4: per-connection forwarded-packet counters, a QACK sent
every QACK_INTERVAL packets to either a fixed target (static method) or the
argmax connection (dynamic method), using TCP timestamp-echo spoofing to give
the sender a tiny RTT sample.

Usage (inside the switch netns):
    python3 qack_proxy.py static|dynamic

Known simplification (see docs/OBSERVATIONS.md item 9 for full detail): the
spoofed QACK's own TCP seq/TSval are set to the *last genuinely observed*
values from that receiver's real ACKs (not synthesized), which is safe
(worst case a stale-looking packet is just ignored by the sender's PAWS check)
but means the QACK occasionally has no effect if a fresher real ACK already
raised the sender's cached timestamp — acceptable for this fast-path
replication, called out explicitly rather than presented as exact.
"""
import sys
import threading
from scapy.all import sniff, send, IP, TCP

IFACE = "sw-se"
SENDER_IP = "10.0.0.2"
CONNS = {0: "10.0.1.2", 1: "10.0.2.2", 2: "10.0.3.2"}  # Receiver1/2/3
IP_TO_IDX = {v: k for k, v in CONNS.items()}
QACK_INTERVAL = 1024  # packets, per paper Section IV
STATIC_TARGET = 0     # Receiver1 (80ms / largest RTT), per paper's static method

mode = sys.argv[1] if len(sys.argv) > 1 else "dynamic"
assert mode in ("static", "dynamic")

lock = threading.Lock()
counters = {0: 0, 1: 0, 2: 0}
last_cum_ack = {0: 0, 1: 0, 2: 0}
last_sender_tsval = {0: 0, 1: 0, 2: 0}   # from sender's data packets -> used as TSecr
last_recv_seq = {0: 0, 1: 0, 2: 0}       # from receiver's real ACKs
last_recv_tsval = {0: 0, 1: 0, 2: 0}     # from receiver's real ACKs -> used as our TSval
sender_port = {0: None, 1: None, 2: None}
recv_port = {0: None, 1: None, 2: None}
global_count = 0
qack_sent_total = 0


def get_ts_option(tcp_layer):
    for opt in tcp_layer.options:
        if opt[0] == "Timestamp":
            return opt[1]
    return None


def send_qack(idx):
    global qack_sent_total
    if sender_port[idx] is None or recv_port[idx] is None:
        return  # haven't observed this connection's ports yet; skip this round
    pkt = IP(src=CONNS[idx], dst=SENDER_IP) / TCP(
        sport=recv_port[idx],
        dport=sender_port[idx],
        flags="A",
        seq=last_recv_seq[idx],
        ack=last_cum_ack[idx],
        window=65535,
        options=[("Timestamp", (last_recv_tsval[idx], last_sender_tsval[idx]))],
    )
    send(pkt, iface=IFACE, verbose=0)
    qack_sent_total += 1
    print(f"[qack_proxy] QACK #{qack_sent_total} -> conn{idx} ({CONNS[idx]}) "
          f"counters={counters}", flush=True)


def fire_qack_and_reset():
    global global_count
    target = STATIC_TARGET if mode == "static" else max(counters, key=lambda k: counters[k])
    send_qack(target)
    global_count = 0
    for k in counters:
        counters[k] = 0


def pkt_callback(pkt):
    global global_count
    if IP not in pkt or TCP not in pkt:
        return
    ip, tcp = pkt[IP], pkt[TCP]
    ts = get_ts_option(tcp)

    if ip.src == SENDER_IP and ip.dst in IP_TO_IDX:
        idx = IP_TO_IDX[ip.dst]
        payload_len = len(tcp.payload)
        with lock:
            sender_port[idx] = tcp.sport
            recv_port[idx] = tcp.dport
            if payload_len > 0:
                counters[idx] += 1
                last_cum_ack[idx] = tcp.seq + payload_len
                if ts:
                    last_sender_tsval[idx] = ts[0]
                global_count += 1
                if global_count >= QACK_INTERVAL:
                    fire_qack_and_reset()
    elif ip.dst == SENDER_IP and ip.src in IP_TO_IDX:
        idx = IP_TO_IDX[ip.src]
        with lock:
            last_recv_seq[idx] = tcp.seq
            if ts:
                last_recv_tsval[idx] = ts[0]


if __name__ == "__main__":
    print(f"[qack_proxy] mode={mode} interval={QACK_INTERVAL} iface={IFACE}", flush=True)
    sniff(iface=IFACE, filter="tcp", prn=pkt_callback, store=False)
