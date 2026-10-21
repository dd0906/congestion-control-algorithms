"""
run_experiment.py  –  End-to-end experiment runner
====================================================
Runs the full QUIC-DC experiment pipeline:
  Step 1 → Run simulation (quic_dc_sim.py)
  Step 2 → Generate graphs (plot_results.py)
  Step 3 → Print summary table

Usage (from the scripts/ folder):
  python run_experiment.py

Or from quic_dc_experiment/:
  python scripts/run_experiment.py
"""

import os
import sys
import time
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_step(step_name: str, module_path: str):
    print(f"\n{'='*60}")
    print(f"  {step_name}")
    print(f"{'='*60}")
    t0 = time.perf_counter()
    result = subprocess.run(
        [sys.executable, module_path],
        cwd=SCRIPT_DIR,
        capture_output=False
    )
    elapsed = time.perf_counter() - t0
    if result.returncode != 0:
        print(f"\n[ERROR] {step_name} failed (exit {result.returncode})")
        sys.exit(result.returncode)
    print(f"\n  [OK] Completed in {elapsed:.1f}s")
    return elapsed


def print_summary_table():
    import csv
    raw_dir = os.path.join(SCRIPT_DIR, "..", "raw_outputs", "summary_all.csv")
    if not os.path.exists(raw_dir):
        print("  [WARN] summary_all.csv not found – run simulation first")
        return

    with open(raw_dir, newline="") as f:
        rows = list(csv.DictReader(f))

    # Show 4BDP results only (matches paper Table 1)
    subset = [r for r in rows if r["buffer"] == "4.0BDP"]
    if not subset:
        subset = rows[:8]

    header = f"\n{'Algorithm':<25} {'Goodput':>10} {'Med RTT':>10} {'P95 RTT':>10} {'Loss%':>10}"
    sep    = "-" * len(header)
    print(f"\n{'='*60}")
    print("  Summary (Buffer = 4x BDP, 25 Mbps link, RTT_min=50ms)")
    print(f"  Matching paper Table 1 scenario")
    print(f"{'='*60}")
    print(header)
    print(sep)
    for r in subset:
        print(f"  {r['name']:<23} {float(r['goodput_mbps']):>9.2f}  "
              f"{float(r['median_rtt_ms']):>9.1f}  "
              f"{float(r['p95_rtt_ms']):>9.1f}  "
              f"{float(r['loss_pct']):>9.4f}")
    print(f"\n  Units: Goodput=Mbps, RTT=ms, Loss=%")


def main():
    print("=" * 62)
    print("  QUIC-DC Experiment Runner")
    print("  Based on: arXiv:2507.00896")
    print("=" * 62)
    print(f"\nPython: {sys.version}")
    print(f"Working directory: {SCRIPT_DIR}")

    t_total = time.perf_counter()

    run_step("Step 1/2: Running QUIC-DC simulation",
             os.path.join(SCRIPT_DIR, "quic_dc_sim.py"))

    run_step("Step 2/2: Generating graphs",
             os.path.join(SCRIPT_DIR, "plot_results.py"))

    print_summary_table()

    total_elapsed = time.perf_counter() - t_total
    print(f"\n{'='*60}")
    print(f"  All done in {total_elapsed:.1f}s")
    print(f"  Raw data:  quic_dc_experiment/raw_outputs/")
    print(f"  Graphs:    quic_dc_experiment/graphs/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
