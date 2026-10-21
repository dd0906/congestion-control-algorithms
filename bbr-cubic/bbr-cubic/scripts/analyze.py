#!/usr/bin/env python3
"""Analyze BBR-vs-CUBIC coexistence results. Read-only against outputs/.

Usage:
    python3 analyze.py
Reads outputs/{solo_bbr,solo_cubic,conditionA,conditionB}_{bbr,cubic}.json
Writes outputs/*.csv, outputs/summary.json, and the 3 required graphs into ../graphs/
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")
GRAPHS = os.path.join(BASE, "graphs")
os.makedirs(GRAPHS, exist_ok=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(path):
    with open(path) as f:
        return json.load(f)


def per_second(d):
    return [(round(i["sum"]["end"]), i["sum"]["bits_per_second"] / 1e6) for i in d["intervals"]]


def retransmits(d):
    try:
        return d["end"]["sum_sent"]["retransmits"]
    except KeyError:
        return None


def jains_fi(values):
    n = len(values)
    s = sum(values)
    sq = sum(v * v for v in values)
    return (s * s) / (n * sq) if sq > 0 else 0.0


def analyze_coexist(label, rate, delay):
    bbr = load(os.path.join(OUT, f"{label}_bbr.json"))
    cubic = load(os.path.join(OUT, f"{label}_cubic.json"))
    bbr_ts = dict(per_second(bbr))
    cubic_ts = dict(per_second(cubic))
    common = sorted(set(bbr_ts) & set(cubic_ts))

    rows = []
    for t in common:
        b, c = bbr_ts[t], cubic_ts[t]
        fi = jains_fi([b, c])
        rows.append((t, b, c, fi))

    csv_path = os.path.join(OUT, f"{label}_timeseries.csv")
    with open(csv_path, "w") as f:
        f.write("elapsed_s,bbr_mbps,cubic_mbps,fairness_index\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")

    avg_bbr = sum(r[1] for r in rows) / len(rows)
    avg_cubic = sum(r[2] for r in rows) / len(rows)
    avg_fi = sum(r[3] for r in rows) / len(rows)
    bbr_retr = retransmits(bbr)
    cubic_retr = retransmits(cubic)

    summary = {
        "label": label, "rate_mbit": rate, "delay_ms": delay,
        "avg_bbr_mbps": avg_bbr, "avg_cubic_mbps": avg_cubic,
        "avg_fairness_index": avg_fi,
        "bbr_retransmits": bbr_retr, "cubic_retransmits": cubic_retr,
    }
    with open(os.path.join(OUT, f"{label}_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # Chart
    times = [r[0] for r in rows]
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(times, [r[1] for r in rows], label="BBR", color="tab:blue")
    ax1.plot(times, [r[2] for r in rows], label="CUBIC", color="tab:orange")
    ax1.set_xlabel("Elapsed Time [s]")
    ax1.set_ylabel("Throughput [Mbit/s]")
    ax1.set_ylim(0, max([r[1] for r in rows] + [r[2] for r in rows] + [1]) * 1.2)
    ax2 = ax1.twinx()
    ax2.plot(times, [r[3] for r in rows], label="Fairness Index", color="tab:red", linewidth=1)
    ax2.set_ylabel("Jain's Fairness Index")
    ax2.set_ylim(0, 1.05)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
    plt.title(f"BBR vs CUBIC coexistence — {label} ({rate} Mbit/s, {delay} ms RTT)")
    plt.tight_layout()
    png = os.path.join(GRAPHS, f"bbr_vs_cubic_{label}.png")
    plt.savefig(png, dpi=150)
    plt.close()
    print(f"{label}: BBR avg={avg_bbr:.2f}Mbps CUBIC avg={avg_cubic:.2f}Mbps FI={avg_fi:.3f} "
          f"BBR_retr={bbr_retr} CUBIC_retr={cubic_retr} -> {png}")
    return summary


def analyze_solo(label, tag):
    d = load(os.path.join(OUT, f"{label}_{tag}.json"))
    avg = d["end"]["sum_received"]["bits_per_second"] / 1e6
    retr = retransmits(d)
    print(f"{label} ({tag} alone): avg={avg:.2f}Mbps retransmits={retr}")
    return {"label": label, "tag": tag, "avg_mbps": avg, "retransmits": retr}


if __name__ == "__main__":
    solo_bbr = analyze_solo("solo_bbr", "bbr")
    solo_cubic = analyze_solo("solo_cubic", "cubic")
    condA = analyze_coexist("conditionA", 10, 20)
    condB = analyze_coexist("conditionB", 5, 50)

    # Fairness comparison chart across the two coexistence conditions
    fig, ax = plt.subplots(figsize=(6, 5))
    labels = ["Condition A\n(10Mbit/20ms)", "Condition B\n(5Mbit/50ms)"]
    values = [condA["avg_fairness_index"], condB["avg_fairness_index"]]
    bars = ax.bar(labels, values, color=["tab:blue", "tab:orange"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Jain's Fairness Index (BBR vs CUBIC)")
    ax.set_title("BBR vs CUBIC Fairness — Condition Comparison")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.3f}", ha="center")
    plt.tight_layout()
    fair_png = os.path.join(GRAPHS, "bbr_cubic_fairness_comparison.png")
    plt.savefig(fair_png, dpi=150)
    print(f"Wrote {fair_png}")

    with open(os.path.join(OUT, "all_summary.json"), "w") as f:
        json.dump({"solo_bbr": solo_bbr, "solo_cubic": solo_cubic,
                    "conditionA": condA, "conditionB": condB}, f, indent=2)
