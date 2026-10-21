#!/usr/bin/env python3
"""Compute Jain's Fairness Index over time from per-flow iPerf3 JSON logs and
reproduce Fig. 3 (bar chart, average fairness index) / Fig. 4 & 5 (per-flow
throughput + fairness index over time) style charts from OUR measured data.

Input: for one scenario, three iperf3 client JSON logs (one per receiver,
started with `iperf3 -J`), each covering the same 600s run.

Usage:
    python3 analyze_results.py <scenario_name> \
        <receiver1_80ms.json> <receiver2_40ms.json> <receiver3_20ms.json> \
        <output_dir> [split_s]

split_s (default 300, matching the paper's 600s/QACK-at-300s runs) is the
elapsed-time boundary used for the pre/post-QACK-enable average fairness
windows. Our time-budget-scaled runs use 120s total with QACK enabled at
60s, so pass 60 for those. See docs/OBSERVATIONS.md item 9.

Outputs (into <output_dir>):
    <scenario_name>_timeseries.csv   elapsed_s, thr_80ms, thr_40ms, thr_20ms, fairness_index
    <scenario_name>_throughput.png   Fig. 4/5-style chart
    <scenario_name>_summary.json     average fairness index overall, and for [0,split_s)s / [split_s,end)s

See docs/PROJECT_PLAN.md section 4.5 for why Jain's Fairness Index is the
assumed metric (the paper does not name the formula explicitly).
"""
import json
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_intervals_mbps(json_path):
    """Return list of (elapsed_end_seconds, mbit_per_sec) from an iperf3 -J log."""
    with open(json_path) as f:
        data = json.load(f)
    out = []
    for interval in data["intervals"]:
        s = interval["sum"]
        end_t = s["end"]
        mbps = s["bits_per_second"] / 1e6
        out.append((round(end_t), mbps))
    return out


def jains_fairness_index(values):
    n = len(values)
    if n == 0:
        return 0.0
    s = sum(values)
    sq = sum(v * v for v in values)
    if sq == 0:
        return 0.0
    return (s * s) / (n * sq)


def main():
    if len(sys.argv) not in (6, 7):
        print(__doc__)
        sys.exit(1)

    scenario, f80, f40, f20, outdir = sys.argv[1:6]
    split_s = int(sys.argv[6]) if len(sys.argv) == 7 else 300
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    series_80 = dict(load_intervals_mbps(f80))
    series_40 = dict(load_intervals_mbps(f40))
    series_20 = dict(load_intervals_mbps(f20))

    common_times = sorted(set(series_80) & set(series_40) & set(series_20))
    if not common_times:
        print("ERROR: no overlapping timestamps between the three iperf3 logs.")
        sys.exit(1)

    rows = []
    for t in common_times:
        thr = [series_80[t], series_40[t], series_20[t]]
        fi = jains_fairness_index(thr)
        rows.append((t, thr[0], thr[1], thr[2], fi))

    csv_path = outdir / f"{scenario}_timeseries.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["elapsed_s", "thr_80ms_mbps", "thr_40ms_mbps", "thr_20ms_mbps", "fairness_index"])
        w.writerows(rows)

    def avg_fi(lo, hi):
        vals = [r[4] for r in rows if lo <= r[0] < hi]
        return sum(vals) / len(vals) if vals else None

    summary = {
        "scenario": scenario,
        "n_samples": len(rows),
        "split_s": split_s,
        "avg_fairness_index_overall": avg_fi(0, 10**9),
        "avg_fairness_index_pre_split": avg_fi(0, split_s),
        "avg_fairness_index_post_split": avg_fi(split_s, 10**9),
    }
    with open(outdir / f"{scenario}_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))

    # Fig. 4 / Fig. 5 style chart: 3 throughput lines + fairness index on secondary axis.
    times = [r[0] for r in rows]
    thr80 = [r[1] for r in rows]
    thr40 = [r[2] for r in rows]
    thr20 = [r[3] for r in rows]
    fis = [r[4] for r in rows]

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.plot(times, thr80, label="80ms", color="tab:blue")
    ax1.plot(times, thr40, label="40ms", color="tab:orange")
    ax1.plot(times, thr20, label="20ms", color="tab:green")
    ax1.set_xlabel("Elapsed Time [s]")
    ax1.set_ylabel("Throughput [Mbit/s]")
    ax1.set_xlim(0, max(times) if times else 600)
    ax1.set_ylim(0, max(thr80 + thr40 + thr20 + [1]) * 1.15)

    ax2 = ax1.twinx()
    ax2.plot(times, fis, label="Fairness Index", color="tab:red", linewidth=1)
    ax2.set_ylabel("Fairness Index")
    ax2.set_ylim(0, 1.05)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    plt.title(f"Throughput trend — {scenario}")
    plt.tight_layout()
    png_path = outdir / f"{scenario}_throughput.png"
    plt.savefig(png_path, dpi=150)
    print(f"Wrote {csv_path}, {png_path}, {outdir / (scenario + '_summary.json')}")


if __name__ == "__main__":
    main()
