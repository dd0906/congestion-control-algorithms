"""
plot_results.py  –  Generate graphs from QUIC-DC simulation output
===================================================================
Reads CSV files from ../raw_outputs/ and produces publication-quality
graphs matching the style of arXiv:2507.00896 (Mascolo et al.).

Figures generated:
  Fig 1: RTT CDF comparison (all algorithms, 4BDP buffer) — matches paper Fig 4
  Fig 2: Throughput over time (QUIC-DC 80% vs Cubic vs BBRv2, 4BDP)
  Fig 3: Goodput & Loss rate bar chart (4BDP buffer)
  Fig 4: RTT CDF (2BDP buffer) — matches paper Fig 5 scenario
  Fig 5: Cwnd dynamics over time (QUIC-DC 80% vs Westwood+, 2BDP)
  Fig 6: Loss rate vs buffer size (all algorithms)
  Fig 7: Goodput vs buffer size heatmap

Usage:
  python plot_results.py
"""

import csv
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")   # non-interactive backend for headless/Windows
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Paths ────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
RAW_DIR      = os.path.join(SCRIPT_DIR, "..", "raw_outputs")
GRAPH_DIR    = os.path.join(SCRIPT_DIR, "..", "graphs")
os.makedirs(GRAPH_DIR, exist_ok=True)

# ── Colour palette (paper-like) ──────────────────────────────────────────
PALETTE = {
    "QUIC-DC (10%)": "#d62728",
    "QUIC-DC (20%)": "#ff7f0e",
    "QUIC-DC (50%)": "#e377c2",
    "QUIC-DC (80%)": "#2ca02c",
    "Cubic"        : "#1f77b4",
    "BBRv2"        : "#9467bd",
    "NewReno"      : "#8c564b",
    "Westwood+"    : "#17becf",
}
LS = {
    "QUIC-DC (10%)": "-.",
    "QUIC-DC (20%)": "--",
    "QUIC-DC (50%)": ":",
    "QUIC-DC (80%)": "-",
    "Cubic"        : "-",
    "BBRv2"        : "--",
    "NewReno"      : ":",
    "Westwood+"    : "-.",
}

# ── Helpers ──────────────────────────────────────────────────────────────

def load_timeseries(label: str, algo_name: str) -> list[dict]:
    safe = (algo_name.replace("/","_").replace(" ","_")
            .replace("(","").replace(")","").replace("%","pct"))
    path = os.path.join(RAW_DIR, f"timeseries_{label}_{safe}.csv")
    if not os.path.exists(path):
        print(f"  [WARN] missing: {path}")
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_summary() -> list[dict]:
    path = os.path.join(RAW_DIR, "summary_all.csv")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def cdf(values: list[float]):
    s = sorted(values)
    y = np.arange(1, len(s) + 1) / len(s)
    return s, y


def save(fig, name: str, dpi: int = 150):
    path = os.path.join(GRAPH_DIR, name)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ── Figure 1: RTT CDF (4BDP buffer) ─────────────────────────────────────
def fig_rtt_cdf(buf_label: str, title_suffix: str):
    algos = list(PALETTE.keys())
    fig, ax = plt.subplots(figsize=(8, 5))
    for algo in algos:
        rows = load_timeseries(buf_label, algo)
        if not rows:
            continue
        rtts = [float(r["rtt_ms"]) for r in rows]
        xs, ys = cdf(rtts)
        ax.plot(xs, ys, linestyle=LS[algo], color=PALETTE[algo],
                label=algo, linewidth=1.8)

    ax.set_xlabel("RTT (ms)", fontsize=12)
    ax.set_ylabel("CDF", fontsize=12)
    ax.set_title(f"RTT CDF – {title_suffix}", fontsize=13)
    ax.legend(fontsize=9, loc="lower right")
    ax.grid(True, alpha=0.35)
    ax.set_xlim(left=0)
    ax.set_ylim(0, 1.05)
    return fig


# ── Figure 2: Throughput time series ────────────────────────────────────
def fig_throughput_time(buf_label: str, title_suffix: str,
                        selected=("QUIC-DC (80%)", "Cubic", "BBRv2", "Westwood+")):
    fig, ax = plt.subplots(figsize=(8, 4))
    for algo in selected:
        rows = load_timeseries(buf_label, algo)
        if not rows:
            continue
        t  = [float(r["time_ms"]) / 1000 for r in rows]
        tp = [float(r["throughput_mbps"]) for r in rows]
        # smooth
        window = max(1, len(tp) // 30)
        tp_sm  = np.convolve(tp, np.ones(window)/window, mode="same").tolist()
        ax.plot(t, tp_sm, color=PALETTE.get(algo,"grey"),
                linestyle=LS.get(algo,"-"), label=algo, linewidth=1.8)

    ax.axhline(25, color="black", linestyle=":", linewidth=1.2, label="Link capacity (25 Mbps)")
    ax.set_xlabel("Time (s)", fontsize=12)
    ax.set_ylabel("Throughput (Mbps)", fontsize=12)
    ax.set_title(f"Throughput over Time – {title_suffix}", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.35)
    ax.set_ylim(bottom=0)
    return fig


# ── Figure 3: Goodput & Loss bar chart ──────────────────────────────────
def fig_goodput_loss_bar(buf_label: str, title_suffix: str, summaries: list[dict]):
    rows = [s for s in summaries if s["buffer"] == buf_label]
    names     = [r["name"] for r in rows]
    goodputs  = [float(r["goodput_mbps"]) for r in rows]
    loss_pcts = [float(r["loss_pct"]) for r in rows]

    x = np.arange(len(names))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Goodput
    colors_g = [PALETTE.get(n, "#888888") for n in names]
    bars = ax1.bar(x, goodputs, width=0.6, color=colors_g, edgecolor="black", linewidth=0.7)
    ax1.axhline(25, color="red", linestyle="--", linewidth=1.2, label="Link cap")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax1.set_ylabel("Goodput (Mbps)", fontsize=11)
    ax1.set_title(f"Goodput – {title_suffix}", fontsize=12)
    ax1.legend(fontsize=9)
    ax1.grid(axis="y", alpha=0.35)
    for bar, val in zip(bars, goodputs):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                 f"{val:.1f}", ha="center", va="bottom", fontsize=8)

    # Loss rate
    colors_l = [PALETTE.get(n, "#888888") for n in names]
    bars2 = ax2.bar(x, loss_pcts, width=0.6, color=colors_l, edgecolor="black", linewidth=0.7)
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax2.set_ylabel("Packet Loss (%)", fontsize=11)
    ax2.set_title(f"Packet Loss – {title_suffix}", fontsize=12)
    ax2.grid(axis="y", alpha=0.35)
    for bar, val in zip(bars2, loss_pcts):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                 f"{val:.3f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    return fig


# ── Figure 4: CWND dynamics ──────────────────────────────────────────────
def fig_cwnd_dynamics(buf_label: str, title_suffix: str,
                      selected=("QUIC-DC (80%)", "Westwood+", "Cubic")):
    fig, axes = plt.subplots(len(selected), 1, figsize=(9, 3.5 * len(selected)),
                             sharex=True)
    if len(selected) == 1:
        axes = [axes]

    for ax, algo in zip(axes, selected):
        rows = load_timeseries(buf_label, algo)
        if not rows:
            continue
        t    = [float(r["time_ms"]) / 1000 for r in rows]
        cwnd = [float(r["cwnd_bytes"]) / 1024 for r in rows]  # KB
        rtt  = [float(r["rtt_ms"]) for r in rows]
        ax2  = ax.twinx()
        ax.plot(t, cwnd, color=PALETTE.get(algo,"blue"), label="CWND (KB)", linewidth=1.5)
        ax2.plot(t, rtt, color="orange", linestyle="--", label="RTT (ms)", linewidth=1.2, alpha=0.75)
        ax.set_ylabel("CWND (KB)", fontsize=10, color=PALETTE.get(algo,"blue"))
        ax2.set_ylabel("RTT (ms)", fontsize=10, color="orange")
        ax.set_title(f"{algo} – {title_suffix}", fontsize=11)
        ax.grid(True, alpha=0.3)
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")

    axes[-1].set_xlabel("Time (s)", fontsize=11)
    fig.tight_layout()
    return fig


# ── Figure 5: Loss rate vs Buffer size ──────────────────────────────────
def fig_loss_vs_buffer(summaries: list[dict]):
    buf_labels = ["0.5BDP", "1.0BDP", "2.0BDP", "4.0BDP"]
    algos      = list(PALETTE.keys())

    fig, ax = plt.subplots(figsize=(9, 5))
    for algo in algos:
        losses = []
        for bl in buf_labels:
            row = next((s for s in summaries
                        if s["name"] == algo and s["buffer"] == bl), None)
            losses.append(float(row["loss_pct"]) if row else 0.0)
        ax.plot(range(len(buf_labels)), losses,
                color=PALETTE[algo], linestyle=LS[algo],
                marker="o", label=algo, linewidth=1.8)

    ax.set_xticks(range(len(buf_labels)))
    ax.set_xticklabels(buf_labels, fontsize=10)
    ax.set_xlabel("Buffer Size", fontsize=12)
    ax.set_ylabel("Packet Loss (%)", fontsize=12)
    ax.set_title("Packet Loss Rate vs Buffer Size", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.35)
    return fig


# ── Figure 6: Goodput vs Buffer size ────────────────────────────────────
def fig_goodput_vs_buffer(summaries: list[dict]):
    buf_labels = ["0.5BDP", "1.0BDP", "2.0BDP", "4.0BDP"]
    algos      = list(PALETTE.keys())

    fig, ax = plt.subplots(figsize=(9, 5))
    for algo in algos:
        gps = []
        for bl in buf_labels:
            row = next((s for s in summaries
                        if s["name"] == algo and s["buffer"] == bl), None)
            gps.append(float(row["goodput_mbps"]) if row else 0.0)
        ax.plot(range(len(buf_labels)), gps,
                color=PALETTE[algo], linestyle=LS[algo],
                marker="s", label=algo, linewidth=1.8)

    ax.axhline(25, color="black", linestyle=":", linewidth=1.2, label="Link capacity")
    ax.set_xticks(range(len(buf_labels)))
    ax.set_xticklabels(buf_labels, fontsize=10)
    ax.set_xlabel("Buffer Size", fontsize=12)
    ax.set_ylabel("Goodput (Mbps)", fontsize=12)
    ax.set_title("Goodput vs Buffer Size (25 Mbps link)", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.35)
    ax.set_ylim(0, 30)
    return fig


# ── Figure 7: OWQD over time (QUIC-DC variants only) ────────────────────
def fig_owqd_time(buf_label: str, title_suffix: str):
    dc_algos = [a for a in PALETTE if a.startswith("QUIC-DC")]
    fig, ax  = plt.subplots(figsize=(8, 4))
    for algo in dc_algos:
        rows = load_timeseries(buf_label, algo)
        if not rows:
            continue
        t    = [float(r["time_ms"]) / 1000 for r in rows]
        owqd = [float(r["owqd_ms"]) for r in rows]
        # Draw threshold line
        # threshold = frac × buf_time_ms; derive from data max
        ax.plot(t, owqd, color=PALETTE[algo], linestyle=LS[algo],
                label=algo, linewidth=1.5)

    ax.set_xlabel("Time (s)", fontsize=12)
    ax.set_ylabel("OWQD (ms)", fontsize=12)
    ax.set_title(f"One-Way Queueing Delay – {title_suffix}", fontsize=13)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.35)
    ax.set_ylim(bottom=0)
    return fig


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print("Loading summary data …")
    summaries = load_summary()

    generated = []

    print("Generating figures …")

    f = fig_rtt_cdf("4.0BDP", "Buffer=4×BDP, 25 Mbps, RTT_min=50 ms")
    generated.append(save(f, "fig1_rtt_cdf_4BDP.png"))

    f = fig_rtt_cdf("2.0BDP", "Buffer=2×BDP, 25 Mbps, RTT_min=50 ms")
    generated.append(save(f, "fig2_rtt_cdf_2BDP.png"))

    f = fig_throughput_time("4.0BDP", "Buffer=4×BDP")
    generated.append(save(f, "fig3_throughput_time_4BDP.png"))

    f = fig_throughput_time("2.0BDP", "Buffer=2×BDP")
    generated.append(save(f, "fig4_throughput_time_2BDP.png"))

    f = fig_goodput_loss_bar("4.0BDP", "Buffer=4×BDP", summaries)
    generated.append(save(f, "fig5_goodput_loss_4BDP.png"))

    f = fig_goodput_loss_bar("2.0BDP", "Buffer=2×BDP", summaries)
    generated.append(save(f, "fig6_goodput_loss_2BDP.png"))

    f = fig_cwnd_dynamics("2.0BDP", "Buffer=2×BDP",
                          selected=["QUIC-DC (80%)", "Westwood+", "Cubic"])
    generated.append(save(f, "fig7_cwnd_dynamics_2BDP.png"))

    f = fig_loss_vs_buffer(summaries)
    generated.append(save(f, "fig8_loss_vs_buffer.png"))

    f = fig_goodput_vs_buffer(summaries)
    generated.append(save(f, "fig9_goodput_vs_buffer.png"))

    f = fig_owqd_time("4.0BDP", "Buffer=4×BDP")
    generated.append(save(f, "fig10_owqd_time_4BDP.png"))

    print(f"\n{len(generated)} figures saved to: {GRAPH_DIR}")
    return generated


if __name__ == "__main__":
    main()
