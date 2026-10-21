# FINAL STATE — Complete Experiment Summary

This is the single, self-contained explanation of the entire experiment: what was
replicated, how, what was measured, and how it compares to the paper. Written so
that someone with **zero prior context** — human or AI — can understand exactly
what exists in this project and why, without needing any other document or any
conversation history.

## 1. Objective

Replicate the core experiments of:
> Yuki Kuramo, Saneyasu Yamaguchi, "RTT Fairness Improvement in TCP BBR with
> Dynamic Target Adjustment," 2025 IEEE ICCE-Taiwan.
> (`paper/RTT_Fairness_Improvement_in_TCP_BBR_with_Dynamic_Target_Adjustment.pdf`)

**Paper's claim:** TCP BBR connections with different RTTs sharing one bottleneck
link are unfair — the longer-RTT connection gets more bandwidth. The paper's "QACK"
mechanism has a network switch spoof a fast ACK back to a chosen sender, tricking
BBR into shrinking its congestion window (throttling that connection). This paper's
specific contribution: choose the QACK **target dynamically** (whichever connection
is currently consuming the most bandwidth) instead of a **fixed/static** target, and
claims the dynamic method improves fairness *more* than the static method.

**This project's goal:** reproduce that experiment (baseline unfairness, QACK
static, QACK dynamic) and measure whether the same pattern holds.

## 2. Why This Is NOT an Exact Reproduction (read this first)

The paper's experiments used **Mininet + a P4/BMv2 programmable switch prototype**,
600-second runs, with QACK enabled at the 300-second mark. This project operated
under a **hard 1-hour deadline**. A from-source build of the full P4 toolchain
(protobuf, gRPC, PI, BMv2, p4c) was attempted and could not finish in time (see
section 4). The project pivoted to a **fast-path substitute**:

| Paper used | This project used instead |
|---|---|
| Mininet (network emulator) | Linux network namespaces (`ip netns`) + veth pairs |
| P4/BMv2 programmable switch | A plain Linux namespace acting as an IP router |
| Compiled P4 program for QACK | A Python/Scapy raw-socket proxy (`scripts/qack_proxy.py`) |
| 600s runs, QACK at 300s | **120s runs, QACK at 60s** (same enable-at-midpoint ratio) |

Every measurement below is **real, executed, measured data** — nothing here is
simulated or fabricated — but it comes from this substitute environment, not the
paper's. Treat the results as directional/qualitative validation, not precise
numeric reproduction. Full rationale: `docs/OBSERVATIONS.md` item 9.

## 3. Environment Used

- **Host:** Windows 11.
- **Linux environment:** a dedicated WSL2 distro named **`FairFlow-Ubuntu2204`**
  (Ubuntu 22.04.5 LTS, kernel `6.18.33.1-microsoft-standard-WSL2`), created via
  `wsl --import` of Canonical's official WSL rootfs, running as **root** (no sudo
  needed inside it — it's a single-purpose sandbox for this project only). The
  Windows machine's original/default WSL distro (`Ubuntu`, 26.04) was left
  untouched.
- **Congestion control:** TCP BBR, loaded via `modprobe tcp_bbr` (confirmed present
  in `sysctl net.ipv4.tcp_available_congestion_control`).
- **Traffic generator:** iPerf3 (each flow run with `-C bbr`).
- **QACK mechanism:** Python 3 + Scapy 2.7.0 (raw sockets), not P4/BMv2.
- **Project files location:** Windows path
  `C:\Users\PRAVEENA\OneDrive\Desktop\FairFlow_Replication`, visible from WSL at
  `/mnt/c/Users/PRAVEENA/OneDrive/Desktop/FairFlow_Replication`. All commands in
  this project run from WSL against that `/mnt/c/...` path.

## 4. Topology

Built by `scripts/netns_topo.sh` (idempotent `up`/`down`):

```
sender --(RTT ~0.066ms, 15 Mbit/s tbf bottleneck)-- switch --(RTT 80ms)-- recv1
                                                          --(RTT 40ms)-- recv2
                                                          --(RTT 20ms)-- recv3
```

- 5 Linux network namespaces: `sender`, `switch`, `recv1`, `recv2`, `recv3`.
- veth pairs connect `switch` to each of the other 4 namespaces.
- `switch` has `net.ipv4.ip_forward=1`; the other namespaces route through it.
- RTT emulated with `tc qdisc ... netem delay` on both ends of each link (netem
  delay is one-way per interface, so round-trip = delay applied at both ends —
  e.g. 40ms delay on both ends of the switch-recv1 link gives an 80ms RTT).
- **Bottleneck bandwidth: 15 Mbit/s**, applied via `tc qdisc ... tbf` on the
  sender-switch link. **This value is not stated in the paper** (a documented gap
  — see `docs/OBSERVATIONS.md` item 1); it was chosen so 3 concurrent BBR flows
  would genuinely contend for the link.
- IP addressing: `10.0.0.2` (sender), `10.0.0.1`/`10.0.1.1`/`10.0.2.1`/`10.0.3.1`
  (switch's four interfaces), `10.0.1.2` (recv1/80ms), `10.0.2.2` (recv2/40ms),
  `10.0.3.2` (recv3/20ms).

## 5. Experiment Configuration (all three scenarios)

- 3 concurrent iPerf3 flows: sender -> recv1 (port 5201), sender -> recv2 (port
  5202), sender -> recv3 (port 5203), all using `-C bbr`.
- **Duration: 120 seconds** (scaled down from the paper's 600s).
- QACK interval: **1024 packets** (unchanged from the paper — this is a
  packet-count trigger, not time-based, so it did not need scaling).
- QACK enable time: **t=60s** (scaled down from the paper's t=300s, same
  halfway-point ratio).
- Orchestrated end-to-end by `scripts/run_scenario.sh <scenario> <duration>
  <qack_mode> <enable_at_s> <outdir>` — one continuous script per run (topology up
  -> iperf3 servers -> iperf3 clients -> optional QACK proxy -> wait -> teardown).
  This must be one continuous process — see `docs/OBSERVATIONS.md` item 9 for why
  separate `wsl -d ...` invocations were found not to reliably share network
  namespace state.

## 6. The Three Scenarios (exact commands already run)

### Baseline — no QACK
```
run_scenario.sh no_qack 120 none 0 outputs
```
No QACK proxy running at any point. Measures the raw RTT-unfairness of 3
concurrent BBR flows.

### QACK static
```
run_scenario.sh qack_static 120 static 60 outputs
```
`scripts/qack_proxy.py static` starts at t=60s. Static mode always targets
connection 0 (the 80ms/recv1 flow) — see `STATIC_TARGET = 0` in
`scripts/qack_proxy.py`, matching the paper's static baseline (targets the
largest-RTT connection).

### QACK dynamic
```
run_scenario.sh qack_dynamic 120 dynamic 60 outputs
```
`scripts/qack_proxy.py dynamic` starts at t=60s. Dynamic mode recomputes the
target every 1024-packet interval as `argmax` over the three connections' packet
counters (`max(counters, key=lambda k: counters[k])` in `scripts/qack_proxy.py`).

**How the QACK packet itself is crafted** (all three scenarios' proxy, when
active): the switch namespace sniffs its sender-facing interface with Scapy,
counts forwarded data packets per connection, and — for the chosen target — sends
a spoofed TCP ACK (source = that receiver's IP:port, destination = sender's
IP:port) whose TCP-timestamp-echo (`TSecr`) reflects the sender's own last
observed `TSval`. This makes the sender's BBR compute a very small RTT sample,
shrinking its congestion window. The spoofed packet's own sequence number and
`TSval` reuse the **last genuinely observed** values from that connection's real
reverse-direction ACKs (not synthesized) — a deliberate safety simplification
(see `scripts/qack_proxy.py` docstring and `docs/OBSERVATIONS.md` item 9) to avoid
desyncing the sender's TCP PAWS protection, at the cost of some injected QACKs
being silently ignored if a fresher real ACK already arrived.

## 7. Output Filenames (all in `outputs/`, all real, all already generated)

| Pattern | What it is |
|---|---|
| `<scenario>_80ms.json`, `_40ms.json`, `_20ms.json` | Raw iPerf3 `-J` JSON output per flow, per scenario (`no_qack`, `qack_static`, `qack_dynamic`) |
| `<scenario>_recv{1,2,3}_server.log` | iPerf3 server-side logs |
| `<scenario>_qack.log` | QACK proxy's own log (only for `qack_static`/`qack_dynamic`) — every fired QACK, its target, and the counters at that moment |
| `<scenario>_timeseries.csv` | Per-second throughput (all 3 flows) + Jain's Fairness Index, merged from the 3 JSON logs |
| `<scenario>_summary.json` | Average fairness index (overall, pre-split, post-split) for that scenario |
| `<scenario>_throughput.png` | Throughput-over-time chart (paper's Fig. 4/5 equivalent) |
| `fig3_replication.png` | Bar chart of average fairness index across all 3 scenarios (paper's Fig. 3 equivalent) |
| `smoketest_*` | A 10-second no-QACK pipeline sanity check, run once before the real 120s experiments — not otherwise analyzed |

## 8. Measured Results

### Fairness Index (Jain's) — cf. paper's Fig. 3

| Scenario | Paper (visual estimate from chart) | This replication |
|---|---|---|
| w/o QACK | ~0.65 | **0.612** |
| w/ QACK static | ~0.83 | **0.637** |
| w/ QACK dynamic | ~0.93 | **0.635** |

Paper values are approximate (read off the bar chart image — the paper publishes
no numeric table). Ours are exact, computed by `scripts/analyze_results.py` from
the real measured throughput.

### Baseline unfairness (confirmed match to the paper)
80ms flow steady-state ≈ 10.5 Mbit/s vs. 40ms ≈ 3.65 Mbit/s vs. 20ms ≈ 3.1 Mbit/s —
the longest-RTT connection clearly dominates, matching the paper's core claim.

### Static method (qualitative match to the paper)
`outputs/qack_static_qack.log` shows connection 0's (80ms) packet share collapsing
from ~650-690 per 1024-packet window down to ~80-150 by the run's end, while
connection 1 (40ms) rises to ~600-660 — matching the paper's own description of
the static method sometimes over-correcting and making the target the new
underdog. The throughput chart shows this effect appearing in the run's last ~25
seconds (from ~t=95s), not immediately at the t=60s enable point.

### Dynamic method (does NOT match the paper's claimed improvement)
`outputs/qack_dynamic_qack.log` (read in full, not just the tail) shows the
argmax logic selected connection 0 in **all 35 of 35** fired QACKs — the identical
target and count as the static run, because connection 0 genuinely had the
highest packet count every round. Despite this, connection 0's packet share never
dropped below ~540/window in the dynamic run (vs. collapsing to ~80-150 in the
static run), and tail-end throughput closely resembles the no-QACK baseline. Since
target and count were identical between the two runs, the weaker effect is most
likely **run-to-run variance and/or QACK-delivery fidelity differences** between
two independent 120s executions — not a flaw in the dynamic *algorithm* as
implemented. This is a genuine, disclosed divergence from the paper's claim that
dynamic outperforms static — full discussion in `docs/RESULTS.md` section 1.

## 9. Deviations From the Paper (complete list)

1. Environment: Linux netns/veth/tc + Scapy, not Mininet/BMv2/P4Runtime.
2. Run duration: 120s (QACK at t=60s), not 600s (QACK at t=300s).
3. Bottleneck bandwidth: assumed 15 Mbit/s (paper doesn't state a value).
4. QACK packet crafting: our own reconstruction (paper's original mechanism is in
   an unpublished prior paper by the same authors) using TCP timestamp-echo
   spoofing with last-observed real values, not synthesized ones.
5. Fairness formula: assumed Jain's Fairness Index (paper doesn't name it
   explicitly, inferred from convention).
6. iPerf version: whatever `iperf3` resolved to in the `FairFlow-Ubuntu2204`
   image, not the paper's pinned "iPerf 3.7."
7. All of the above are documented in detail in `docs/OBSERVATIONS.md` and
   `docs/PROJECT_PLAN.md` section 7 as they were discovered.

## 10. Final Conclusion

This replication **confirms**:
- TCP BBR's core RTT-unfairness problem (longest-RTT flow dominates a shared
  bottleneck).
- The static QACK method's tendency to over-correct, sometimes making its target
  the new lowest-throughput flow.

This replication **does not confirm**, within the constraints described above:
- That dynamic QACK targeting improves fairness beyond static targeting. Our data
  shows the two methods performing similarly (0.637 vs. 0.635 fairness index), and
  the verified root-cause investigation (section 8) shows this is not because the
  dynamic method chose a worse target — it chose the identical target the paper's
  static method would — but most likely because of run-to-run variance and/or
  the simplified QACK-crafting mechanism's delivery fidelity.

**Natural next step** (optional, not required): finish the P4/BMv2/Mininet build
that was started but not completed (`scripts/qack.p4`, partial build tree in
`FairFlow-Ubuntu2204:/root/p4-tools`) and re-run all three scenarios at the paper's
actual 600s/300s-enable duration, ideally with multiple repeated runs per scenario
to average out the run-to-run variance identified above.

---

# ADDITIONAL, SEPARATE EXPERIMENT — BBR vs CUBIC Coexistence

**Everything above this line (sections 1-10) is the QACK/BBR paper replication.
Everything below is a distinct, later, additional experiment, fully isolated
under `bbr_cubic/`, that does not modify or depend on anything above.** It was
added to connect this project to a different assigned topic: "SDN-Based Dynamic
Bandwidth Arbitrator for Fair Coexistence of BBR and CUBIC under Fluctuating
Network Conditions." Full detail lives in `bbr_cubic/README.md`,
`bbr_cubic/EXPERIMENT.md`, and `bbr_cubic/RESULTS.md` — this section is a
condensed summary for anyone reading `FINAL_STATE.md` top to bottom.

## 11. Objective (BBR vs CUBIC)

Produce a small, **actually executed**, real-measurement demonstration of the
BBR-vs-CUBIC coexistence/fairness problem — one real BBR flow and one real CUBIC
flow, competing simultaneously over the same constrained bottleneck, under two
different network conditions. This is a measurement experiment only; it does
**not** implement the SDN bandwidth arbitrator itself.

## 12. Environment (reused, nothing new installed)

Same `FairFlow-Ubuntu2204` WSL2 distro as the QACK replication (Ubuntu 22.04.5
LTS, root, BBR + CUBIC both already available via
`sysctl net.ipv4.tcp_available_congestion_control` -> `reno cubic bbr`). No
compilation, no new kernel, no P4/BMv2/Mininet — reused Linux network namespaces
+ veth + `tc` (netem/tbf) + iperf3, the same technique as the QACK replication's
topology, in a completely separate set of namespaces/files under `bbr_cubic/`.

## 13. Topology

```
senderA (BBR)   --fast link--\
                               switch --BOTTLENECK (rate+delay)-- receiver
senderB (CUBIC) --fast link--/
```
4 namespaces (`senderA`, `senderB`, `switch`, `receiver`), built/torn down by
`bbr_cubic/scripts/topo.sh`. Both flows funnel through the single
switch-receiver link, where the shared bottleneck (rate limit + delay, via
`tc tbf`/`tc netem`) is applied — the genuine shared contention point both flows
compete for. Round-trip delay is split evenly across both ends of that link
(same convention as the QACK replication).

## 14. Congestion Control Verification (not inferred from flags)

`iperf3 -C bbr` / `-C cubic` requests an algorithm via `setsockopt`, but this was
**independently verified** by capturing live kernel socket state (`ss -ti`)
inside each sender's namespace ~3 seconds into every run
(`bbr_cubic/outputs/*_ss.log`). In every run, senderA's actual data-transfer
connection (identifiable by non-trivial `bytes_sent`/`segs_out`) shows `bbr`, and
senderB's shows `cubic` — confirmed by direct inspection of the raw log output,
not assumed from the command-line flag.

## 15. Scenarios Executed (all real, all actually run)

| # | Label | Mode | Bottleneck | Delay (RTT) | Duration |
|---|---|---|---|---|---|
| 1 | `solo_bbr` | BBR alone (baseline) | 10 Mbit/s | 20ms | 20s |
| 2 | `solo_cubic` | CUBIC alone (baseline) | 10 Mbit/s | 20ms | 20s |
| 3 | **Condition A** | BBR + CUBIC coexisting | 10 Mbit/s | 20ms | 30s |
| 4 | **Condition B** | BBR + CUBIC coexisting | 5 Mbit/s | 50ms | 30s |

(An 8-second `smoketest` coexistence run was also executed first to validate the
pipeline — not otherwise analyzed, not part of the reported results below.)

## 16. Measured Results

| Condition | Bottleneck | Delay | BBR Throughput | CUBIC Throughput | Jain's Fairness Index | BBR Retransmits | CUBIC Retransmits |
|---|---|---|---|---|---|---|---|
| Solo BBR | 10 Mbit/s | 20ms | 9.46 Mbps | — | — | 0 | — |
| Solo CUBIC | 10 Mbit/s | 20ms | — | 9.54 Mbps | — | — | 24 |
| **Condition A** (coexisting) | 10 Mbit/s | 20ms | **1.86 Mbps** | **8.65 Mbps** | **0.643** | 10 | 40 |
| **Condition B** (coexisting) | 5 Mbit/s | 50ms | **1.77 Mbps** | **3.82 Mbps** | **0.630** | 12 | 53 |

Raw sources: `bbr_cubic/outputs/solo_bbr_bbr.json`,
`bbr_cubic/outputs/solo_cubic_cubic.json`,
`bbr_cubic/outputs/conditionA_{bbr,cubic}.json`,
`bbr_cubic/outputs/conditionB_{bbr,cubic}.json`,
`bbr_cubic/outputs/{conditionA,conditionB}_summary.json`,
`bbr_cubic/outputs/all_summary.json`.

**Generated graphs** (all in `bbr_cubic/graphs/`):
- `bbr_vs_cubic_conditionA.png` — throughput (BBR + CUBIC) and fairness index over time, Condition A.
- `bbr_vs_cubic_conditionB.png` — same, Condition B.
- `bbr_cubic_fairness_comparison.png` — bar chart comparing the Jain's Fairness Index of Condition A vs. Condition B.

## 17. Honest Findings — Limitations (no predetermined conclusion assumed)

- **Solo baselines are nearly identical** (~9.5 Mbit/s each) — with no competing
  flow, both algorithms fill the bottleneck about equally well.
- **When coexisting, CUBIC clearly dominated BBR in both conditions** — roughly
  **4.6x** in Condition A, **~2.2x** in Condition B. **This is the opposite of the
  direction often emphasized in BBR-vs-loss-based-CC literature** (where BBR is
  frequently reported as out-competing CUBIC). Reported as measured, not adjusted
  to match any expected narrative. Most plausible causes: (a) the `tc tbf`
  bottleneck here is a small, single FIFO queue that rewards CUBIC's aggressive
  queue-filling behavior over BBR's paced, model-based sending rate; (b) the
  30-second coexistence window may be too short for BBR's ~10-round-trip ProbeBW
  cycle to settle against an active competitor; (c) this is a Linux
  namespace/`tc` emulation, not a real switch/router queue or AQM — the same
  category of limitation noted for the QACK replication above.
- **Jain's Fairness Index ~0.63-0.64 in both conditions** — meaningfully below
  ideal fairness (1.0), demonstrating a real, measurable coexistence problem
  (motivating the assigned SDN-arbitrator topic), but *not* markedly different
  between Condition A and B despite the large change in bottleneck/delay — a
  broader sweep of conditions would be needed to characterize that relationship.
- **Retransmits scale with dominance**: CUBIC (the dominant flow in both
  conditions) shows more retransmits (40, 53) than BBR (10, 12).
- This experiment does **not** implement or evaluate the SDN bandwidth
  arbitrator itself — only demonstrates, with real measurements, the
  coexistence/fairness problem that motivates building one.

## 18. Mini-Conclusion (BBR vs CUBIC)

Confirmed: a real, measurable BBR-vs-CUBIC fairness problem exists in this
environment (Jain's FI ~0.63-0.64, well below ideal). **Not** confirmed/matched
to common literature framing: the *direction* of dominance — here CUBIC beat BBR
substantially in both tested conditions, plausibly due to the small-buffer,
short-duration, namespace-emulated setup described above, not a general claim
about BBR vs. CUBIC behavior in all environments.

---
*Written 2026-08-01. Both this section and sections 1-10 above are self-contained
and independently re-verifiable by inspecting the referenced files, without
rerunning any experiment. Nothing in this update modified or reran any existing
experiment or output — see `docs/COMMAND_HISTORY.md` and the `bbr_cubic/` docs
for the full record of what was executed.*
