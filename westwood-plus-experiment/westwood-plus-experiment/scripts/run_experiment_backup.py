#!/usr/bin/env python3

import csv
import json
import os
import time
from datetime import datetime

from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.link import TCLink
from mininet.log import setLogLevel, info

BASE = "/home/karnika/westwood-plus-experiment"
RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)

# Initial validation: one 100 MB transfer per algorithm.
TRIALS = 1
TRANSFER = "100M"
DURATION_SECONDS = 20
BANDWIDTH_MBPS = 25
ONE_WAY_DELAY = "25ms"
QUEUE_PACKETS = 420

def run_experiment():
    csv_path = os.path.join(RESULTS, "westwood_vs_reno.csv")
    timestamp = datetime.now().isoformat(timespec="seconds")

    rows = []

    net = Mininet(
        controller=None,
        link=TCLink,
        switch=OVSBridge,
        autoSetMacs=True
    )

    h1 = net.addHost("h1", ip="10.0.0.1/24")
    h2 = net.addHost("h2", ip="10.0.0.2/24")
    s1 = net.addSwitch("s1")

    # Each link has 25 Mbps capacity and 25 ms delay.
    # The approximate unloaded RTT is therefore 50 ms.
    net.addLink(
        h1, s1, cls=TCLink,
        bw=BANDWIDTH_MBPS, delay=ONE_WAY_DELAY,
        max_queue_size=QUEUE_PACKETS
    )
    net.addLink(
        h2, s1, cls=TCLink,
        bw=BANDWIDTH_MBPS, delay=ONE_WAY_DELAY,
        max_queue_size=QUEUE_PACKETS
    )

    try:
        info("*** Starting Mininet\n")
        net.start()

        info("*** Testing host connectivity\n")
        loss = net.ping([h1, h2])
        if loss != 0:
            raise RuntimeError(
                f"Host connectivity test failed: {loss}% packet loss"
            )

        available = h1.cmd(
            "sysctl -n net.ipv4.tcp_available_congestion_control"
        ).strip().split()

        info(f"*** Sender available algorithms: {available}\n")

        for algorithm in ["westwood", "reno"]:
            if algorithm not in available:
                raise RuntimeError(
                    f"{algorithm} is not available inside h1: {available}"
                )

            for trial in range(1, TRIALS + 1):
                info(
                    f"\n*** Algorithm={algorithm}, trial={trial}\n"
                )

                # Confirm the algorithm can be selected on the sender.
                setting = h1.cmd(
                    f"sysctl -w "
                    f"net.ipv4.tcp_congestion_control={algorithm}"
                ).strip()
                info(setting + "\n")

                # Start a one-shot iperf3 server on the receiver.
                server = h2.popen(
                    ["iperf3", "-s", "-1", "-p", "5201"],
                    stdout=None,
                    stderr=None
                )
                time.sleep(1)

                # Use a fixed-size bulk transfer and request JSON output.
                command = [
                    "iperf3", "-c", "10.0.0.2",
                    "-p", "5201",
                    "-n", TRANSFER,
                    "-C", algorithm,
                    "-J"
                ]

                output = h1.cmd(" ".join(command))
                try:
                    data = json.loads(output)
                except json.JSONDecodeError:
                    server.terminate()
                    raise RuntimeError(
                        "iperf3 did not return valid JSON:\n" + output[-2000:]
                    )

                if "error" in data:
                    server.terminate()
                    raise RuntimeError(data["error"])

                end = data.get("end", {})
                summary = end.get("sum_sent", {})
                received = end.get("sum_received", {})

                # iperf3 reports bits/sec; convert to Mbps.
                goodput_mbps = received.get("bits_per_second", 0) / 1e6
                sent_mbps = summary.get("bits_per_second", 0) / 1e6
                retransmits = summary.get("retransmits", 0)
                transfer_seconds = summary.get("seconds", 0)
                sent_bytes = summary.get("bytes", 0)
                received_bytes = received.get("bytes", 0)
                row = {
                    "sent_bytes": sent_bytes,
                    "received_bytes": received_bytes,
                    "timestamp": timestamp,
                    "algorithm": algorithm,
                    "trial": trial,
                    "configured_bandwidth_mbps": BANDWIDTH_MBPS,
                    "one_way_delay_ms": 25,
                    "queue_packets_per_link": QUEUE_PACKETS,
                    "transfer_size": TRANSFER,
                    "goodput_mbps": round(goodput_mbps, 4),
                    "sender_rate_mbps": round(sent_mbps, 4),
                    "retransmissions": retransmits,
                    "transfer_seconds": round(transfer_seconds, 4),
                    "iperf_cpu_percent": end.get("cpu_utilization_percent", {}).get(
                        "host_total", None
                    )
                }
                rows.append(row)

                # Save each result immediately so earlier runs are retained.
                write_header = not os.path.exists(csv_path)
                with open(csv_path, "a", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=row.keys())
                    if write_header:
                        writer.writeheader()
                    writer.writerow(row)

                info(
                    f"*** {algorithm}: goodput={goodput_mbps:.3f} Mbps, "
                    f"retransmissions={retransmits}, "
                    f"duration={transfer_seconds:.2f} s\n"
                )

                try:
                    server.wait(timeout=5)
                except Exception:
                    server.terminate()

        info(f"\n*** Results saved to {csv_path}\n")

    finally:
        net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    run_experiment()
