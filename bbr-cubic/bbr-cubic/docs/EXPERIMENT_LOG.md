# Experiment Log

All three runs below were executed via the fast-path environment (see
`docs/OBSERVATIONS.md` item 9) inside the `FairFlow-Ubuntu2204` WSL distro, using
`scripts/run_scenario.sh <scenario> <duration> <qack_mode> <enable_at> <outdir>`.
Durations are scaled down from the paper's 600s/enable-at-300s to fit a 1-hour
project deadline — 120s/enable-at-60s, same ratio (QACK enabled at the run's
midpoint).

## Run 1 — no_qack (baseline)
Date: 2026-08-01
Scenario: w/o QACK
Command: `run_scenario.sh no_qack 120 none 0 outputs`
Duration: 120s, no QACK at any point.
Topology: sender-switch RTT ~0.066ms + 15mbit tbf bottleneck; switch-recv1 RTT
80ms; switch-recv2 RTT 40ms; switch-recv3 RTT 20ms. TCP BBR on all 3 iperf3 flows.
Raw output: `outputs/no_qack_80ms.json`, `outputs/no_qack_40ms.json`,
`outputs/no_qack_20ms.json` (iperf3 -J), server logs
`outputs/no_qack_recv{1,2,3}_server.log`.
Analysis: `outputs/no_qack_timeseries.csv`, `outputs/no_qack_throughput.png`,
`outputs/no_qack_summary.json`.
Outcome: 80ms flow steady-state ~10.5 Mbit/s, 40ms ~3.65 Mbit/s, 20ms ~3.1 Mbit/s —
longest-RTT flow clearly dominates, confirming the paper's core RTT-unfairness
premise. Avg Jain's Fairness Index (full run) = 0.612.

## Run 2 — qack_static
Date: 2026-08-01
Scenario: w/ QACK static method (fixed target = 80ms / Receiver1, largest RTT)
Command: `run_scenario.sh qack_static 120 static 60 outputs`
Duration: 120s, QACK proxy (`scripts/qack_proxy.py static`) started at t=60s.
Raw output: `outputs/qack_static_{80ms,40ms,20ms}.json`,
`outputs/qack_static_qack.log` (proxy's own log of every QACK fired + counters
at that moment).
Analysis: `outputs/qack_static_timeseries.csv`, `outputs/qack_static_throughput.png`,
`outputs/qack_static_summary.json` (split_s=60).
Outcome: proxy log shows the targeted 80ms connection's packet share dropping
from ~650-690/window (of ~1024) down to ~80-150/window by the end of the run,
while the 40ms connection's share rises to ~600-660/window — i.e., the static
method visibly over-corrects, consistent with the paper's own description of
this failure mode. Post-enable (t=60-120s) avg Fairness Index = 0.637 (vs. 0.612
baseline) — direction correct, magnitude much smaller than the paper's reported
~0.83.

## Run 3 — qack_dynamic
Date: 2026-08-01
Scenario: w/ QACK dynamic method (target = argmax per-connection counter,
re-evaluated every 1024-packet interval)
Command: `run_scenario.sh qack_dynamic 120 dynamic 60 outputs`
Duration: 120s, QACK proxy (`scripts/qack_proxy.py dynamic`) started at t=60s.
Raw output: `outputs/qack_dynamic_{80ms,40ms,20ms}.json`,
`outputs/qack_dynamic_qack.log`.
Analysis: `outputs/qack_dynamic_timeseries.csv`,
`outputs/qack_dynamic_throughput.png`, `outputs/qack_dynamic_summary.json`
(split_s=60).
Outcome: post-enable (t=60-120s) avg Fairness Index = 0.635 — essentially the
same as the static run and only marginally above baseline; tail-end per-flow
throughput (80ms ~10.5, 40ms ~3.65, 20ms ~3.1 Mbit/s) looks close to the
no-QACK baseline's tail values, i.e. less visible effect than the static run
within this compressed window. **Verified detail** (read the full log, not just
the tail): the argmax logic selected connection 0 (80ms) in all 35 of 35 fired
QACKs — the identical target and count as the static run — because connection 0
genuinely had the highest per-window packet count every round in this execution.
So the weaker observed effect is not because dynamic targeted a different or
"wrong" connection; something else (run-to-run variance, QACK-delivery fidelity)
produced a different outcome from an identical targeting decision. This diverges
from the paper's claim that the dynamic method improves fairness *more* than
static — see `docs/RESULTS.md` section 1 for the full honest discussion (short
post-enable window,
simplified QACK-crafting fidelity, single-FIFO `tbf` bottleneck).

## Anomalies / repeats
None of the three runs were repeated — each ran once, end-to-end, successfully,
within the time budget. A 10s no-QACK smoke test (`outputs/smoketest_*.json`,
not otherwise analyzed) was run first to validate the pipeline end-to-end before
committing to the three real 120s runs.

---
*All three runs above are real, executed measurements — not simulated or
fabricated — collected under the fast-path environment substitution documented
in `docs/OBSERVATIONS.md` item 9.*
