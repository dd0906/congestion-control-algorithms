#!/usr/bin/env python3
"""Reproduce the paper's Fig. 3 (bar chart of average Fairness Index across the
three scenarios) from our own measured summary JSONs (produced by
analyze_results.py).

Usage:
    python3 make_fig3.py <no_qack_summary.json> <static_summary.json> \
        <dynamic_summary.json> <output_png>

Which fairness-index window to use per scenario:
  - no_qack: avg_fairness_index_overall (whole 600s run has no QACK)
  - static/dynamic: avg_fairness_index_300_600s (QACK is enabled at ~300s;
    the paper's Fig. 3 bars represent the "with QACK" steady-state effect,
    so we use the post-enable window for an apples-to-apples comparison
    against the no-QACK baseline's full-run average).
See docs/RESULTS.md for the side-by-side numeric comparison against the
paper's (visually-estimated) Fig. 3 values.
"""
import json
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    no_qack_path, static_path, dynamic_path, out_png = sys.argv[1:]

    with open(no_qack_path) as f:
        no_qack = json.load(f)
    with open(static_path) as f:
        static = json.load(f)
    with open(dynamic_path) as f:
        dynamic = json.load(f)

    labels = ["w/o QACK", "w QACK static\nmethod", "w QACK dynamic\nmethod"]
    values = [
        no_qack["avg_fairness_index_overall"],
        static["avg_fairness_index_post_split"],
        dynamic["avg_fairness_index_post_split"],
    ]

    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(labels, values, color=["tab:green", "tab:blue", "tab:red"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Fairness Index")
    ax.set_title("Fairness Index (our replication)")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.3f}", ha="center")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    print(f"Wrote {out_png}")
    print(json.dumps(dict(zip(["no_qack", "static", "dynamic"], values)), indent=2))


if __name__ == "__main__":
    main()
