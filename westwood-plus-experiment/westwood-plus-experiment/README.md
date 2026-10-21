# TCP Westwood vs. TCP Reno: Mininet Experiment

A small experiment comparing TCP Westwood and TCP Reno using Mininet and `iperf3`.

> **Status: Preliminary.** Current receiver-throughput values differ, but sender/receiver byte counters do not reconcile and congestion-control labels are missing from the captured client JSON. Do not treat the comparison as a validated conclusion until these issues are investigated.

## Objectives

- Create a two-host Mininet topology.
- Test TCP Westwood and TCP Reno using `iperf3`.
- Record receiver throughput across repeated trials.
- Preserve client/server JSON evidence and generate comparison graphs.
- Document measurement limitations.

## Environment

The experiment was run in Ubuntu under WSL2.

| Parameter | Configuration |

| Kernel | Linux `6.6.87.2-microsoft-standard-WSL2` |
| Mininet | 2.3.0 (from the working setup notes) |
| iperf3 | 3.9 |
| Topology | `h1 — s1 — h2` |
| Switch | OVSBridge |
| Host `h1` | `10.0.0.1/24` |
| Host `h2` | `10.0.0.2/24` |
| Link bandwidth | 25 Mbps per host link |
| Configured link delay | 25 ms per host link |
| Queue limit | 420 packets per host link |
| Algorithms | Westwood and Reno |
| Timed tests | 20 seconds per trial, 3 trials per algorithm |

The delay is configured on each host-to-switch link. Actual end-to-end delay depends on the topology and Mininet link configuration.

## Repository Layout

```text
westwood-plus-experiment/
├── scripts/
│   ├── run_experiment.py
│   ├── run_experiment_validated.py
│   └── make_graphs.py
├── results/
│   ├── westwood_vs_reno_validated_v2.csv
│   └── selected iperf3 client/server JSON files
├── graphs/
│   ├── throughput_trials.png
│   └── mean_throughput.png

```

The listed layout is a suggested organization; filenames may differ in your checkout. Keep raw data that supports the results being discussed, and avoid committing obsolete duplicate CSVs or temporary diagnostic output.

## Setup

Requirements:

- Mininet and Open vSwitch
- `iperf3`
- Python 3
- Python package `matplotlib` for graph generation

Check versions:

```bash
iperf3 --version
mn --version
python3 --version
```

Check available TCP congestion-control algorithms:

```bash
sysctl net.ipv4.tcp_available_congestion_control
```

The working environment reported `reno`, `cubic`, and `westwood` as available.

## Running the Experiment

Clean up stale Mininet state:

```bash
sudo mn -c
```

Run the timed experiment:

```bash
cd ~/westwood-plus-experiment
sudo python3 scripts/run_experiment_validated.py
```

The script writes to:

```text
results/westwood_vs_reno_validated_v2.csv
```

It also saves per-trial client and server JSON files. The script refuses to overwrite an existing CSV with the same name. Preserve existing results and change the output filename in the script before a new run if needed.

Generate graphs:

```bash
python3 scripts/make_graphs.py
```

Expected graph files:

- `graphs/throughput_trials.png`
- `graphs/mean_throughput.png`

Check the committed script if output paths or filenames differ.

## Preliminary Findings

The current three-trial receiver-throughput values extracted from server-side summaries are:

| Trial | Westwood| Reno|
| 1 |   16.410 | 23.252 |
| 2 | 16.833 | 23.254 |
| 3 | 16.864 | 23.254 |
| **Mean** | **16.702** | **23.253** |

In these runs, Reno's measured receiver throughput is higher than Westwood's. This is an observation from the current dataset, not proof that Reno is generally superior.

## Validation Issues and Limitations

1. **Sender/receiver byte mismatch:** In an earlier fixed-byte test, the client reported `105,208,624` sender bytes for both algorithms, although `104,857,600` bytes were requested. Client-side receiver summaries were lower: `93,585,408` bytes for Westwood and `94,633,984` bytes for Reno.
2. **Server-side counters need cross-checking:** Separate server JSON files were saved and should be used to compare receiver byte counts with client summaries.
3. **Missing congestion-control labels:** The client JSON contained `sender_tcp_congestion` and `receiver_tcp_congestion` keys, but their values were empty in the captured timed tests. The script issued a sender sysctl setting and iperf3 `-C` option, but the JSON labels alone do not independently prove the active socket setting for every trial.
4. **Retransmissions:** Some summaries reported zero retransmissions. This does not, by itself, explain the counter mismatch or prove there was no data-delivery issue.
5. **HTB warning:** Mininet emitted `sch_htb: quantum of class ... is big` warnings. The experiment ran, but the link queueing configuration should be reviewed.
6. **Unshaped diagnostic:** A separate diagnostic topology without the experiment's configured bandwidth and delay showed implausibly high throughput. Those numbers are excluded from the experiment findings.
7. **Environment:** WSL2 scheduling and virtualization may affect measurements. Only three trials per algorithm are currently reported.

## Evidence

Recommended artifacts for review:

- `results/westwood_vs_reno_validated_v2.csv`
- Selected per-trial client and server JSON files
- `graphs/throughput_trials.png`
- `graphs/mean_throughput.png`
- Screenshots showing congestion-control availability, Mininet connectivity, experiment execution, and validation checks
- The Word report in `report/`, if included in the repository

## Conclusion

The Mininet topology and workflow have been implemented, basic connectivity was verified, six timed tests were run, and preliminary comparison graphs were generated. The results are not fully validated because the sender/receiver byte discrepancy and missing JSON congestion-control labels remain unresolved. Resolve these issues and repeat measurements if necessary before presenting a definitive performance comparison.

## Author / Project Notes

Add the author, course, supervisor, and repository details here if required.
