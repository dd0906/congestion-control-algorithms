# Congestion Control Algorithms: A Comparative Study & Experimental Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Network Emulation: Mininet](https://img.shields.io/badge/Emulator-Mininet-orange.svg)](http://mininet.org/)
[![Simulation: NS--3](https://img.shields.io/badge/Simulator-NS--3-green.svg)](https://www.nsnam.org/)

A comprehensive experimental and comparative benchmarking repository evaluating modern, delay-based, heuristic, and AI/deep reinforcement learning-driven **network congestion control algorithms (CCAs)** across diverse simulated and emulated network topologies (Data Centers, Cellular, LEO Satellite, and Dynamic Bottlenecks).

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Studied Algorithms & Experiments](#-studied-algorithms--experiments)
  - [1. QUIC-DC (QUIC Delay Control)](#1-quic-dc-quic-delay-control)
  - [2. DNCCQ-PPO (Deep Reinforcement Learning for XQUIC)](#2-dnccq-ppo-deep-reinforcement-learning-for-xquic)
  - [3. PowerTCP (Ultra-Low Latency Data Center CCA)](#3-powertcp-ultra-low-latency-data-center-cca)
  - [4. TCP Westwood+ vs. TCP Reno](#4-tcp-westwood-vs-tcp-reno)
  - [5. TCP BBR vs. CUBIC (RTT Fairness)](#5-tcp-bbr-vs-cubic-rtt-fairness)
- [Repository Structure](#-repository-structure)
- [Key Results & Visualizations](#-key-results--visualizations)
- [Quick Start & Reproduction](#-quick-start--reproduction)
- [Prerequisites & Dependencies](#-prerequisites--dependencies)
- [References](#-references)
- [License](#-license)

---

## 🎯 Overview

Internet traffic suffers from throughput degradation and extreme latency inflation (bufferbloat) when mismatched congestion control algorithms encounter varied bottlenecks. Traditional loss-based algorithms (like TCP Reno or CUBIC) aggressively fill bottleneck buffers, introducing queueing delay. Delay-based algorithms and modern learning-based agents attempt to optimize the Tradeoff between throughput and latency along the Kleinrock optimal operational point ($BDP$).

This repository provides **end-to-end reproducible research pipelines, emulation frameworks, protocol implementations, and empirical benchmark results** comparing:
* **Loss-based protocols**: TCP Reno, CUBIC
* **Delay/Rate-based protocols**: QUIC-DC, TCP Westwood+, TIMELY, DX, DCQCN, DCTCP
* **Power & In-Network telemetry protocols**: PowerTCP, Theta-PowerTCP, HPCC
* **Deep Reinforcement Learning (DRL) protocols**: DNCCQ-PPO (Proximal Policy Optimization on XQUIC)

---

## 🔬 Studied Algorithms & Experiments

### 1. QUIC-DC (QUIC Delay Control)
- **Paper Basis:** *QUIC Delay Control: an implementation of congestion and delay control* (Politecnico di Bari, [arXiv:2507.00896](https://arxiv.org/abs/2507.00896)).
- **Focus:** Extends the IETF QUIC protocol with delay-sensitive congestion control via One-Way Queueing Delay (OWQD) and adaptive packet-pacing mechanisms.
- **Location:** `QUIC_DC experiment/`
- **Highlights:** Evaluated over 32 experimental conditions against standard CUBIC and BBR variants across $2\times$ and $4\times$ Bandwidth-Delay Product (BDP) queue limits.

### 2. DNCCQ-PPO (Deep Reinforcement Learning for XQUIC)
- **Focus:** Dynamic network congestion control for the Alibaba **XQUIC** protocol using Proximal Policy Optimization (PPO).
- **Location:** `DNCCQ-PPO-files/`
- **Highlights:**
  - Implements custom OpenAI Gym environments (`gym-rlcc`) integrated directly with Mininet.
  - Multi-agent asynchronous training modules via RLlib and Sample Factory.
  - Native C patch integrating learned neural inference into XQUIC client/server transport routines.

### 3. PowerTCP (Ultra-Low Latency Data Center CCA)
- **Focus:** Next-generation data center congestion control designed to eliminate incast collapses and achieve fast convergence using power-based metrics ($\text{Throughput} / \text{RTT}$).
- **Location:** `PowerTCP-files/`
- **Highlights:**
  - NS-3 discrete-event simulations for 10:1 Incast bursts, multi-flow fairness, and varying traffic workloads.
  - Benchmarked against DCQCN, DCTCP, HPCC, and TIMELY.

### 4. TCP Westwood+ vs. TCP Reno
- **Focus:** Bandwidth estimation-based congestion control versus classic additive-increase/multiplicative-decrease (AIMD).
- **Location:** `westwood-plus-experiment/`
- **Highlights:**
  - Evaluated in Mininet over emulated lossy/delayed links (25 Mbps, 25 ms delay, 420-packet queue).
  - Validated with receiver/sender instrumentation and automated throughput extraction.

### 5. TCP BBR vs. CUBIC (RTT Fairness)
- **Focus:** RTT unfairness mitigation when BBR flows share bottleneck queues with CUBIC or other BBR flows with disparate base RTTs.
- **Location:** `bbr-cubic/`
- **Highlights:**
  - Complete testbed runs measuring RTT inflation, link utilization, and fairness indices under varied buffer and delay regimes.
  - Includes reproduction scripts, condition logs, and analytical writeups.

---

## 📁 Repository Structure

```text
congestion-control-algorithms/
├── .gitignore                          # Standard gitignore (excluding compiled binaries & large dumps)
├── README.md                           # Master repository documentation
├── QUIC_DC experiment/
│   └── QUIC_DC experiment/
│       ├── README.md                   # Detailed experimental guide
│       ├── RESULTS.md                  # Comprehensive numerical performance tables
│       ├── scripts/                    # Simulation & graphing scripts (quic_dc_sim.py, plot_results.py)
│       ├── graphs/                     # 10 publication-quality comparison charts
│       ├── raw_outputs/                # Timeseries CSVs & execution logs
│       └── terminal_screenshots/       # Verified test execution visual logs
├── DNCCQ-PPO-files/
│   └── DNCCQ-PPO/
│       ├── README.md                   # Architecture & setup instructions
│       ├── deploy/                     # Deployment test scripts & model evaluation
│       ├── measureFramework-forxquic/  # Measurement harness & plotting tools
│       ├── rlcc-playground-mininet/    # Mininet network simulation + Gym environment (gym-rlcc)
│       ├── static-build-xquic/         # Static build configuration for XQUIC
│       ├── train-code/                 # PPO training modules (RLlib & Sample Factory)
│       └── xquic_forrlcc/              # XQUIC source modifications with CC hook patches
├── PowerTCP-files/
│   └── examples/PowerTCP/
│       ├── README.md                   # Incast, Fairness & Workload runner guide
│       ├── *.sh                        # Burst, fairness, and workload automation scripts
│       ├── *.py                        # Result parser & plotting routines
│       └── results_*/                  # Processed simulation summaries
├── westwood-plus-experiment/
│   └── westwood-plus-experiment/
│       ├── README.md                   # Mininet reproduction methodology
│       ├── scripts/                    # Validated experiment runners & graph generators
│       ├── results/                    # Validated CSV records & JSON trial logs
│       └── graphs/                     # Throughput & trial variance plots
└── bbr-cubic/
    └── bbr-cubic/
        ├── EXPERIMENT.md               # Methodology & experimental parameters
        ├── docs/                       # Research logs, checklists, and result analysis
        ├── graphs/                     # Fairness & condition comparison figures
        ├── outputs/                    # Output summary logs and raw JSON results
        ├── paper/                      # Reference research literature
        └── scripts/                    # Testbed orchestration scripts
```

---

## 📊 Key Results & Visualizations

### 1. QUIC-DC vs. CUBIC Delay & Throughput Dynamics
QUIC-DC drastically reduces queueing delay (OWQD) and bufferbloat under constrained buffers while maintaining near-line-rate goodput:

| Algorithm | Buffer Size | Avg RTT (ms) | Packet Loss Rate | Relative Goodput |
| :--- | :--- | :--- | :--- | :--- |
| **QUIC-DC** | $2\times$ BDP | **Low / Near Base** | **~0%** | **Optimal** |
| **CUBIC** | $2\times$ BDP | High (Bufferbloat) | Periodic Loss | Suboptimal Under Loss |
| **QUIC-DC** | $4\times$ BDP | Controlled | Minimal | Near Line Rate |

*(Refer to `QUIC_DC experiment/QUIC_DC experiment/graphs/` for full CDF curves and time-series plots)*

### 2. PowerTCP Incast & Fairness
PowerTCP avoids buffer exhaustion in multi-to-one incast patterns by throttling transmission based on instantaneous queuing delay gradients, preventing switch buffer overflow in datacenter fabric topologies.

---

## 🛠️ Quick Start & Reproduction

### Running the QUIC-DC Simulation Pipeline
```bash
cd "QUIC_DC experiment/QUIC_DC experiment"
# Install dependencies
pip install matplotlib numpy aioquic

# Execute full simulation suite and generate graphs
python scripts/run_experiment.py
```

### Running the Mininet Westwood+ vs. Reno Benchmark
```bash
cd "westwood-plus-experiment/westwood-plus-experiment"
# Run validated trials under Mininet (Linux/WSL2)
sudo python3 scripts/run_experiment_validated.py
python3 scripts/make_graphs.py
```

### Training DNCCQ-PPO (Reinforcement Learning)
```bash
cd "DNCCQ-PPO-files/DNCCQ-PPO"
# Install gym environment in editable mode
cd rlcc-playground-mininet/gym-rlcc
pip install -e .

# Launch training using RLlib
cd ../../train-code/rllib/multisteps
python train.py
```

---

## 📦 Prerequisites & Dependencies

* **Linux Environment:** Ubuntu 20.04/22.04 LTS or WSL2 (strongly recommended for Mininet & kernel TCP modules).
* **Python:** Python 3.10 or higher (`numpy`, `matplotlib`, `gym`, `aioquic`, `ray[rllib]`, `torch`).
* **Network Simulators & Tools:**
  * [Mininet](http://mininet.org/) (`mininet`, `openvswitch-switch`, `iperf3`, `iproute2`)
  * [NS-3](https://www.nsnam.org/) (for PowerTCP data center simulations)
  * [XQUIC](https://github.com/alibaba/xquic) build prerequisites (`cmake`, `ninja`, `openssl`, `libevent`)

---

## 📚 References

1. Mascolo, S., Balillo, A. V., Manfredi, G., D'Agostino, D., & De Cicco, L. (2025). *QUIC Delay Control: an implementation of congestion and delay control*. arXiv:2507.00896.
2. Cardwell, N., Cheng, Y., Gunn, C. S., Yeganeh, S. H., & Jacobson, V. (2017). *BBR: Congestion-based congestion control*. ACM Queue, 14(5), 20-53.
3. Ha, S., Rhee, I., & Xu, L. (2008). *CUBIC: a new optimistic congestion control algorithm for high speed networks*. ACM SIGOPS Operating Systems Review, 42(5), 64-74.
4. Alibaba Group. *XQUIC: A cross-platform, high-performance QUIC protocol implementation*.

---

## 📄 License

This repository is licensed under the [MIT License](LICENSE). Individual submodules and patches maintain their respective open-source licensing.
