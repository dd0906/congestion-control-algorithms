import os
import csv
import json
import time
from datetime import datetime

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import OVSBridge
from mininet.log import setLogLevel, info


# Experiment configuration
BASE = "/home/karnika/westwood-plus-experiment"
RESULTS = os.path.join(BASE, "results")

CSV_PATH = os.path.join(
    RESULTS, "westwood_vs_reno_debug.csv"
)

TRIALS = 1
TRANSFER = "100M"
BANDWIDTH_MBPS = 25
ONE_WAY_DELAY = "25ms"
QUEUE_PACKETS = 420
PORT = 5201

ALGORITHMS = ["westwood", "reno"]


def run_experiment():
    os.makedirs(RESULTS, exist_ok=True)

    # Refuse to overwrite a previous debug dataset.
    if os.path.exists(CSV_PATH):
        raise FileExistsError(
            f"{CSV_PATH} already exists. "
            "Rename or back up that file before running again."
        )

    fields = [
        "timestamp",
        "algorithm",
        "trial",
        "configured_bandwidth_mbps",
        "one_way_delay_ms",
        "queue_packets_per_link",
        "transfer_size",
        "sent_bytes",
        "received_bytes",
        "byte_difference",
        "goodput_mbps",
        "sender_rate_mbps",
        "retransmissions",
        "transfer_seconds",
        "iperf_cpu_percent",
    ]

    net = None

    try:
        info("*** Creating Mininet topology\n")

        net = Mininet(
            controller=None,
            link=TCLink,
            switch=OVSBridge,
            autoSetMacs=True,
        )

        h1 = net.addHost("h1", ip="10.0.0.1/24")
        h2 = net.addHost("h2", ip="10.0.0.2/24")
        s1 = net.addSwitch("s1")

        net.addLink(
            h1,
            s1,
            cls=TCLink,
            bw=BANDWIDTH_MBPS,
            delay=ONE_WAY_DELAY,
            max_queue_size=QUEUE_PACKETS,
        )

        net.addLink(
            h2,
            s1,
            cls=TCLink,
            bw=BANDWIDTH_MBPS,
            delay=ONE_WAY_DELAY,
            max_queue_size=QUEUE_PACKETS,
        )

        net.start()

        info("*** Testing connectivity\n")
        dropped = net.pingAll()

        if dropped != 0:
            raise RuntimeError(
                f"Connectivity test failed: {dropped}% packet loss"
            )

        available = h1.cmd(
            "sysctl -n net.ipv4.tcp_available_congestion_control"
        ).strip().split()

        info(f"*** Available algorithms: {available}\n")

        for algorithm in ALGORITHMS:
            if algorithm not in available:
                raise RuntimeError(
                    f"Congestion-control algorithm "
                    f"{algorithm} is unavailable"
                )

        with open(CSV_PATH, "w", newline="") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=fields,
            )
            writer.writeheader()

            for trial in range(1, TRIALS + 1):
                for algorithm in ALGORITHMS:
                    info(
                        f"\n*** Algorithm={algorithm}, "
                        f"trial={trial}\n"
                    )

                    # Configure the sender's default algorithm.
                    setting = h1.cmd(
                        "sysctl -w "
                        f"net.ipv4.tcp_congestion_control={algorithm}"
                    )
                    info(setting)

                    # Start a one-shot iperf3 server.
                    server = h2.popen(
                        [
                            "iperf3",
                            "-s",
                            "-1",
                            "-p",
                            str(PORT),
                        ],
                    )

                    time.sleep(1)

                    command = [
                        "iperf3",
                        "-c",
                        "10.0.0.2",
                        "-p",
                        str(PORT),
                        "-n",
                        TRANSFER,
                        "-C",
                        algorithm,
                        "-J",
                    ]

                    output = h1.cmd(" ".join(command))

                    # Stop the server if it did not exit normally.
                    try:
                        server.wait(timeout=5)
                    except Exception:
                        server.terminate()
                        try:
                            server.wait(timeout=2)
                        except Exception:
                            server.kill()

                    # Parse JSON even if terminal output precedes it.
                    json_start = output.find("{")

                    if json_start == -1:
                        raise RuntimeError(
                            f"No JSON output for {algorithm}:\n{output}"
                        )

                    data = json.loads(output[json_start:])
                    with open(
                         os.path.join(RESULTS, f"iperf3_{algorithm}_debug.json"),
                         "w",
                    ) as json_file:
                         json.dump(data, json_file, indent=2)
                    if "error" in data:
                        raise RuntimeError(data["error"])

                    end = data.get("end", {})
                    summary = end.get("sum_sent", {})
                    received = end.get("sum_received", {})

                    goodput_mbps = (
                        received.get("bits_per_second", 0) / 1e6
                    )
                    sender_mbps = (
                        summary.get("bits_per_second", 0) / 1e6
                    )

                    sent_bytes = summary.get("bytes", 0)
                    received_bytes = received.get("bytes", 0)
                    retransmits = summary.get("retransmits", 0)

                    duration = received.get(
                        "seconds",
                        summary.get("seconds", 0),
                    )

                    byte_difference = sent_bytes - received_bytes

                    cpu = end.get(
                        "cpu_utilization_percent", {}
                    ).get("host_total")

                    row = {
                        "timestamp": datetime.now().isoformat(
                            timespec="seconds"
                        ),
                        "algorithm": algorithm,
                        "trial": trial,
                        "configured_bandwidth_mbps": BANDWIDTH_MBPS,
                        "one_way_delay_ms": 25,
                        "queue_packets_per_link": QUEUE_PACKETS,
                        "transfer_size": TRANSFER,
                        "sent_bytes": sent_bytes,
                        "received_bytes": received_bytes,
                        "byte_difference": byte_difference,
                        "goodput_mbps": round(goodput_mbps, 4),
                        "sender_rate_mbps": round(sender_mbps, 4),
                        "retransmissions": retransmits,
                        "transfer_seconds": round(duration, 4),
                        "iperf_cpu_percent": cpu,
                    }

                    writer.writerow(row)
                    csv_file.flush()

                    info(
                        f"*** {algorithm}: "
                        f"goodput={goodput_mbps:.3f} Mbps, "
                        f"sent={sent_bytes} bytes, "
                        f"received={received_bytes} bytes, "
                        f"byte_difference={byte_difference}, "
                        f"retransmissions={retransmits}, "
                        f"duration={duration:.2f} s\n"
                    )

        info(f"\n*** Results saved to {CSV_PATH}\n")

    finally:
        if net is not None:
            info("*** Stopping Mininet\n")
            net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run_experiment()
