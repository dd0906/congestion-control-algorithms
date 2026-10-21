import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import OVSBridge
from mininet.log import setLogLevel, info


BASE = Path("/home/karnika/westwood-plus-experiment")
RESULTS = BASE / "results"

CSV_PATH = RESULTS / "westwood_vs_reno_validated_v2.csv"

ALGORITHMS = ["westwood", "reno"]
TRIALS = 3
DURATION_SECONDS = 20
BANDWIDTH_MBPS = 25
ONE_WAY_DELAY = "25ms"
QUEUE_PACKETS = 420
PORT = 5201


def save_json(path, data):
    with open(path, "w") as file:
        json.dump(data, file, indent=2)


def run_experiment():
    RESULTS.mkdir(parents=True, exist_ok=True)

    if CSV_PATH.exists():
        raise FileExistsError(
            f"{CSV_PATH} already exists. "
            "Preserve it and choose a new output filename."
        )

    fields = [
        "timestamp", "algorithm", "trial",
        "configured_bandwidth_mbps", "one_way_delay_ms",
        "queue_packets_per_link", "duration_seconds",
        "client_sender_algorithm", "client_receiver_algorithm",
        "sender_bytes", "receiver_bytes", "byte_difference",
        "sender_mbps", "receiver_mbps", "retransmissions",
        "sender_seconds", "receiver_seconds",
        "client_json_valid", "server_json_valid", "status",
    ]

    net = None

    try:
        info("*** Creating experiment topology\n")

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
            h1, s1, cls=TCLink,
            bw=BANDWIDTH_MBPS,
            delay=ONE_WAY_DELAY,
            max_queue_size=QUEUE_PACKETS,
        )
        net.addLink(
            h2, s1, cls=TCLink,
            bw=BANDWIDTH_MBPS,
            delay=ONE_WAY_DELAY,
            max_queue_size=QUEUE_PACKETS,
        )

        net.start()

        dropped = net.pingAll()
        if dropped != 0:
            raise RuntimeError(
                f"Initial connectivity test failed: {dropped}% loss"
            )

        available = h1.cmd(
            "sysctl -n net.ipv4.tcp_available_congestion_control"
        ).strip().split()

        for algorithm in ALGORITHMS:
            if algorithm not in available:
                raise RuntimeError(
                    f"Algorithm unavailable: {algorithm}. "
                    f"Available: {available}"
                )

        with open(CSV_PATH, "x", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fields)
            writer.writeheader()
            csv_file.flush()

            for trial in range(1, TRIALS + 1):
                for algorithm in ALGORITHMS:
                    info(
                        f"\n*** {algorithm.upper()}, trial {trial}/{TRIALS}\n"
                    )

                    setting = h1.cmd(
                        "sysctl -w "
                        f"net.ipv4.tcp_congestion_control={algorithm}"
                    ).strip()
                    info(setting + "\n")

                    active = h1.cmd(
                        "sysctl -n net.ipv4.tcp_congestion_control"
                    ).strip()

                    if active != algorithm:
                        raise RuntimeError(
                            f"Host h1 default is {active}, "
                            f"expected {algorithm}"
                        )

                    prefix = f"iperf3_{algorithm}_trial{trial}_v2"

                    server = h2.popen(
                        [
                            "iperf3", "-s", "-1",
                            "-p", str(PORT), "-J",
                        ],
                        stdout=-1,
                        stderr=-2,
                        text=True,
                    )

                    time.sleep(1)

                    client_output = h1.cmd(
                        "iperf3 -c 10.0.0.2 "
                        f"-p {PORT} -t {DURATION_SECONDS} "
                        f"-C {algorithm} -J"
                    )

                    try:
                        server_output, _ = server.communicate(timeout=10)
                    except Exception:
                        server.terminate()
                        try:
                            server_output, _ = server.communicate(timeout=3)
                        except Exception:
                            server.kill()
                            server_output, _ = server.communicate()

                    client_data = None
                    server_data = None
                    client_error = None
                    server_error = None

                    try:
                        start = client_output.find("{")
                        if start < 0:
                            raise ValueError(
                                "Client produced no JSON object"
                            )
                        client_data = json.loads(client_output[start:])
                    except Exception as exc:
                        client_error = str(exc)

                    try:
                        start = server_output.find("{")
                        if start < 0:
                            raise ValueError(
                                "Server produced no JSON object"
                            )
                        server_data = json.loads(server_output[start:])
                    except Exception as exc:
                        server_error = str(exc)

                    if client_data is not None:
                        save_json(
                            RESULTS / f"{prefix}_client.json",
                            client_data,
                        )
                    if server_data is not None:
                        save_json(
                            RESULTS / f"{prefix}_server.json",
                            server_data,
                        )

                    if client_data is None or server_data is None:
                        raise RuntimeError(
                            f"JSON validation failed for {prefix}. "
                            f"Client: {client_error}; "
                            f"server: {server_error}. "
                            "Inspect the saved terminal output if available."
                        )

                    c_end = client_data.get("end", {})
                    s_end = server_data.get("end", {})

                    sent = c_end.get("sum_sent", {})
                    client_received = c_end.get("sum_received", {})
                    server_received = s_end.get("sum_received", {})
                    server_sent = s_end.get("sum_sent", {})

                    sender_algorithm = client_data.get(
                        "sender_tcp_congestion", ""
                    )
                    receiver_algorithm = client_data.get(
                        "receiver_tcp_congestion", ""
                    )

                    # Client sender counters and server receiver counters
                    # are reported separately for independent comparison.
                    sent_bytes = sent.get("bytes")
                    received_bytes = server_received.get("bytes")

                    sender_rate = sent.get("bits_per_second")
                    receiver_rate = server_received.get("bits_per_second")

                    retransmits = sent.get("retransmits")
                    sender_seconds = sent.get("seconds")
                    receiver_seconds = server_received.get("seconds")

                    difference = (
                        sent_bytes - received_bytes
                        if isinstance(sent_bytes, int)
                        and isinstance(received_bytes, int)
                        else None
                    )

                    errors = []
                    if client_data.get("error"):
                        errors.append("client_error")
                    if server_data.get("error"):
                        errors.append("server_error")
                    if sender_algorithm != algorithm:
                        errors.append("sender_algorithm_mismatch")
                    if not isinstance(sent_bytes, int):
                        errors.append("missing_sender_bytes")
                    if not isinstance(received_bytes, int):
                        errors.append("missing_server_receiver_bytes")
                    if server_received.get("sender") is True:
                        errors.append("server_receiver_flag_unexpected")
                    if difference is not None and difference < 0:
                        errors.append("receiver_bytes_exceed_sender")

                    status = "CHECK_REQUIRED" if errors else "MEASURED_REVIEW_REQUIRED"

                    row = {
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "algorithm": algorithm,
                        "trial": trial,
                        "configured_bandwidth_mbps": BANDWIDTH_MBPS,
                        "one_way_delay_ms": 25,
                        "queue_packets_per_link": QUEUE_PACKETS,
                        "duration_seconds": DURATION_SECONDS,
                        "client_sender_algorithm": sender_algorithm,
                        "client_receiver_algorithm": receiver_algorithm,
                        "sender_bytes": sent_bytes,
                        "receiver_bytes": received_bytes,
                        "byte_difference": difference,
                        "sender_mbps": (
                            round(sender_rate / 1e6, 4)
                            if isinstance(sender_rate, (int, float))
                            else None
                        ),
                        "receiver_mbps": (
                            round(receiver_rate / 1e6, 4)
                            if isinstance(receiver_rate, (int, float))
                            else None
                        ),
                        "retransmissions": retransmits,
                        "sender_seconds": sender_seconds,
                        "receiver_seconds": receiver_seconds,
                        "client_json_valid": True,
                        "server_json_valid": True,
                        "status": status,
                    }

                    writer.writerow(row)
                    csv_file.flush()

                    info(
                        f"*** Sender bytes={sent_bytes}; "
                        f"server receiver bytes={received_bytes}; "
                        f"sender algorithm={sender_algorithm}; "
                        f"receiver label={receiver_algorithm}; "
                        f"status={status}\n"
                    )

                    if errors:
                        info("*** Validation notes: " + ", ".join(errors) + "\n")

                    # Avoid starting the next trial immediately.
                    time.sleep(2)

        info(f"\n*** Results saved to {CSV_PATH}\n")

    finally:
        if net is not None:
            info("*** Stopping Mininet\n")
            net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run_experiment()
