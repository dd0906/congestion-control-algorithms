#!/usr/bin/env python3
"""Verify all Phase 5/6 output artifacts exist, parse, and are non-empty.
Read-only — does not modify or regenerate anything."""
import json
import os
import sys

OUTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/outputs"

RAW_JSON = [
    "no_qack_80ms.json", "no_qack_40ms.json", "no_qack_20ms.json",
    "qack_static_80ms.json", "qack_static_40ms.json", "qack_static_20ms.json",
    "qack_dynamic_80ms.json", "qack_dynamic_40ms.json", "qack_dynamic_20ms.json",
]
SUMMARY_JSON = ["no_qack_summary.json", "qack_static_summary.json", "qack_dynamic_summary.json"]
CSVS = ["no_qack_timeseries.csv", "qack_static_timeseries.csv", "qack_dynamic_timeseries.csv"]
PNGS = ["no_qack_throughput.png", "qack_static_throughput.png", "qack_dynamic_throughput.png", "fig3_replication.png"]
LOGS = ["qack_static_qack.log", "qack_dynamic_qack.log"]

ok = True

print("=== raw iperf3 JSON ===")
for name in RAW_JSON:
    path = os.path.join(OUTDIR, name)
    try:
        with open(path) as f:
            d = json.load(f)
        n_intervals = len(d["intervals"])
        avg = d["end"]["sum_received"]["bits_per_second"] / 1e6
        print(f"OK   {name}  intervals={n_intervals}  avg_mbps={avg:.2f}")
    except Exception as e:
        print(f"FAIL {name}  {e}")
        ok = False

print("\n=== summary JSON ===")
for name in SUMMARY_JSON:
    path = os.path.join(OUTDIR, name)
    try:
        with open(path) as f:
            d = json.load(f)
        print(f"OK   {name}  {d}")
    except Exception as e:
        print(f"FAIL {name}  {e}")
        ok = False

print("\n=== timeseries CSV ===")
for name in CSVS:
    path = os.path.join(OUTDIR, name)
    try:
        with open(path) as f:
            lines = f.readlines()
        print(f"OK   {name}  rows={len(lines)-1}  header={lines[0].strip()}")
        assert len(lines) - 1 == 120, f"expected 120 data rows, got {len(lines)-1}"
    except Exception as e:
        print(f"FAIL {name}  {e}")
        ok = False

print("\n=== PNG charts ===")
for name in PNGS:
    path = os.path.join(OUTDIR, name)
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            magic = f.read(8)
        assert magic == b"\x89PNG\r\n\x1a\n", "bad PNG magic bytes"
        print(f"OK   {name}  {size} bytes, valid PNG signature")
    except Exception as e:
        print(f"FAIL {name}  {e}")
        ok = False

print("\n=== QACK proxy logs ===")
for name in LOGS:
    path = os.path.join(OUTDIR, name)
    try:
        with open(path) as f:
            lines = f.readlines()
        n_fired = sum(1 for l in lines if l.startswith("[qack_proxy] QACK #"))
        print(f"OK   {name}  lines={len(lines)}  qacks_fired={n_fired}")
        assert n_fired > 0, "no QACKs were fired"
    except Exception as e:
        print(f"FAIL {name}  {e}")
        ok = False

print("\n" + ("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
sys.exit(0 if ok else 1)
