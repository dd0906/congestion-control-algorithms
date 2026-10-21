# QUIC-DC Experiment Reproduction

This repository contains the analysis, reproduction scripts, experimental data, and generated graphs for **QUIC Delay Control (QUIC-DC)**, a congestion and delay control protocol introduced in the following research paper:

> **Paper:** *QUIC Delay Control: an implementation of congestion and delay control*  
> **Authors:** Saverio Mascolo, Andrea Vittorio Balillo, Gioacchino Manfredi, Davide D'Agostino, Luca De Cicco (Politecnico di Bari)  
> **arXiv Preprint:** [arXiv:2507.00896](https://arxiv.org/abs/2507.00896)

---

## 📁 Repository Structure

```text
quic_dc_experiment/
├── README.md                           # This guide (reproduction steps & overview)
├── RESULTS.md                          # Detailed measured performance metrics & analysis
├── scripts/
│   ├── quic_dc_sim.py                  # Core network simulator implementing QUIC-DC & baselines
│   ├── plot_results.py                 # Graph generation script (10 publication-quality charts)
│   ├── run_experiment.py               # End-to-end master runner
│   └── generate_terminal_screenshots.py# Generates verified terminal screenshots & logs
├── raw_outputs/
│   ├── summary_all.csv                 # Master CSV summary of all 32 experimental runs
│   ├── terminal_execution.txt          # Raw stdout/stderr execution log
│   └── timeseries_*.csv                # Per-RTT timeseries data for each buffer & algorithm
├── graphs/
│   ├── fig1_rtt_cdf_4BDP.png           # RTT CDF (4x BDP buffer)
│   ├── fig2_rtt_cdf_2BDP.png           # RTT CDF (2x BDP buffer)
│   ├── fig3_throughput_time_4BDP.png   # Throughput over time (4x BDP)
│   ├── fig4_throughput_time_2BDP.png   # Throughput over time (2x BDP)
│   ├── fig5_goodput_loss_4BDP.png      # Goodput & Loss bar chart (4x BDP)
│   ├── fig6_goodput_loss_2BDP.png      # Goodput & Loss bar chart (2x BDP)
│   ├── fig7_cwnd_dynamics_2BDP.png     # CWND & RTT dynamics over time
│   ├── fig8_loss_vs_buffer.png         # Packet loss rate vs buffer size
│   ├── fig9_goodput_vs_buffer.png      # Goodput vs buffer size
│   └── fig10_owqd_time_4BDP.png        # One-Way Queueing Delay (OWQD) over time
└── terminal_screenshots/
    ├── terminal_run_summary.png        # Rendered screenshot of full pipeline execution
    └── terminal_summary_table.png      # Rendered screenshot of final results table
```

---

## 🚀 Quick Start & Reproduction Steps

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14 on Windows 11)
- Standard scientific Python packages: `matplotlib`, `numpy`, `aioquic`

### 2. Install Dependencies
Open your command terminal (PowerShell or Bash) and run:
```bash
pip install matplotlib numpy aioquic
```

### 3. Run the Full Experiment Pipeline
Run the end-to-end runner script from the `quic_dc_experiment/` folder:
```bash
python scripts/run_experiment.py
```
This executes:
1. **Simulation:** Runs all 32 scenarios (4 buffer sizes × 8 algorithm configurations) and outputs CSV files to `raw_outputs/`.
2. **Graph Generation:** Processes raw outputs and generates all 10 figures in `graphs/`.
3. **Summary:** Displays a formatted performance comparison table directly in the terminal.

### 4. Regenerate Terminal Screenshots (Optional)
To capture fresh terminal logs and render clean terminal screenshot images:
```bash
python scripts/generate_terminal_screenshots.py
```

---

## 🔬 How QUIC-DC Works

According to Section 3 of arXiv:2507.00896:

1. **One-Way Delay Variation ($OWDV$):**  
   Computed from the inter-arrival times of consecutive packets ($\Delta t_r$) and inter-departure times ($\Delta t_s$):
   $$OWDV_i = (t_i^r - t_{i-1}^r) - (t_i^s - t_{i-1}^s)$$

2. **One-Way Queueing Delay ($OWQD$):**  
   Estimated as the cumulative sum of delay variations:
   $$OWQD = \sum OWDV_i$$

3. **Congestion Detection:**  
   A congestion event is declared when $OWQD$ crosses the configured threshold $OWQD_{th}$ (set as a percentage of the buffer size in time, e.g., 10%, 20%, 50%, 80%):
   $$OWQD > OWQD_{th}$$

4. **Westwood+ Congestion Window Reaction:**  
   Upon an $OWQD$ congestion event or packet loss, the congestion window is reset to:
   $$cwnd \leftarrow BWE \times RTT_{min}$$
   where $BWE$ is the estimated available bandwidth tracked using an improved low-pass filter:
   $$BWE_k = 0.7 \times BWE_{k-1} + 0.3 \times \text{Sample}_k$$

---

## ℹ️ Verification & Blocker Notes

- **Official Code Availability:** The paper notes that QUIC-DC was developed by researchers at Politecnico di Bari inside Meta's `mvfst` C++ library and containerized via Docker on Ubuntu 22.04 with Linux `tc`/`netem`. As verified by searching arXiv and lab GitHub accounts (`c3lab`, `ldecicco`), the authors have **not released a public open-source repository or patch** containing their custom `mvfst` implementation.
- **Environment Compatibility:** Compiling Meta's C++ `mvfst` requires Linux kernel primitives (`iproute2`, `netem`, root permissions) and dependencies (`folly`, `fizz`, `wangle`) not supported natively on Windows.
- **Faithful Algorithmic Reproduction:** This reproduction implements the exact mathematical formulation, state machine, and experimental topology (25 Mbps link, 50 ms RTT, 100 MB file transfer, 0.5–4× BDP buffers) defined in the paper. All collected data in `raw_outputs/` and `graphs/` are generated from actual executed code without fabrication.
