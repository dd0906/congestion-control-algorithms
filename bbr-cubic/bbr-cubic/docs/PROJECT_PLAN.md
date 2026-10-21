# PROJECT PLAN — FairFlow Replication

Paper: **"RTT Fairness Improvement in TCP BBR with Dynamic Target Adjustment"**
Authors: Yuki Kuramo, Saneyasu Yamaguchi (Kogakuin University)
Venue: 2025 IEEE International Conference on Consumer Electronics – Taiwan (ICCE-Taiwan)
DOI: 10.1109/ICCE-Taiwan66881.2025.11208040
Source file: `paper/RTT_Fairness_Improvement_in_TCP_BBR_with_Dynamic_Target_Adjustment.pdf`

This document is the living record of Phase 2 (methodology extraction) and Phase 3
(replication roadmap). It must be re-read before implementation work and updated if any
new understanding of the paper is gained.

---

## 1. Problem Statement

TCP BBR sets `cwnd = BtlBw × RTprop` (bottleneck bandwidth × min RTT observed in the last
10 seconds). When several TCP BBR flows with **different RTTs** share one bottleneck link,
prior work (Hock et al., ICNP 2017, ref [2] in the paper) showed the **longer-RTT flow
consumes more bandwidth** than shorter-RTT flows — an RTT-fairness violation. Conventional
AQM/packet-drop fairness mechanisms don't help because BBR does not react directly to
packet loss.

The authors' own prior work ("QACK", ref [3], a separate submitted paper we do **not** have
access to) proposed a network-element-side mechanism to throttle a chosen BBR flow by
tricking its sender into observing an artificially small RTT. That prior method picked its
throttling **target statically** (fixed to the largest-RTT flow). This paper's contribution:
make the target-selection **dynamic**, based on measured per-connection bandwidth
consumption, and show it improves fairness further while avoiding the static method's
failure mode (over-throttling the target flow, sometimes to below the other flows).

## 2. Background Mechanism — QACK (prerequisite, from ref [3])

- A network element (switch) sits between sender and receiver(s).
- Normal case: data flows sender→switch→receiver; ACK flows receiver→switch→sender.
- QACK case: when the switch forwards a data packet toward the receiver, it **simultaneously
  generates and sends a spoofed ACK ("QACK", Quick ACK) back to the sender**, immediately,
  without waiting for the real receiver ACK.
- Because the QACK's round-trip time (switch↔sender only) is much smaller than the real
  end-to-end RTT, the BBR sender's RTprop sample drops. Since BBR holds the minimum RTT
  observed for 10 seconds before discarding it, one QACK is enough to depress RTprop (and
  thus `cwnd`, and thus throughput) for up to 10 seconds.
- The interval between QACK packets is a tunable parameter.

## 3. Proposed Method (this paper) — Dynamic QACK Target Selection

### 3.1 Behavior
1. The network element tracks bandwidth consumption **per connection** between one QACK
   event and the next.
2. At each QACK event, the QACK is sent to the sender of **whichever connection consumed
   the most bandwidth** during the preceding interval (i.e., the current "elephant flow").
3. This keeps the throttling target continuously aligned with whichever flow is actually
   dominating the bottleneck, rather than a fixed a-priori guess (e.g., "largest RTT").

### 3.2 Prototype implementation details (P4)
- Implemented in **P4** on a programmable switch prototype.
- The switch **counts packets forwarded per connection** (a running counter per flow).
- On each QACK trigger event:
  - The QACK packet is sent to the sender of the connection with the **largest counter**.
  - **All** per-connection counters are then reset to 0 (not just the winner's).
  - Counters start at 0 at the beginning of the experiment.
- The **set of candidate connections is statically configured** in the prototype (the
  switch knows in advance which flows are eligible); only the **choice of which candidate
  is targeted at each interval** is dynamic. (i.e., dynamic target selection among a
  static candidate list — not dynamic flow discovery.)
- QACK interval used in evaluation: **1024 packets**.

### 3.3 Baseline "static" method (for comparison)
- Same QACK mechanism, but the target connection is **fixed** for the whole run.
- Per ref [2]'s finding ("larger RTT → larger bandwidth consumption"), the static method
  targets the **largest-RTT connection** (Receiver1 / 80 ms path in the evaluation).

## 4. Experimental Setup

### 4.1 Environment
- "Experimental network constructed with virtual machines (VMs) provided by **P4.org**"
  — i.e., the reference environment from `github.com/p4lang/tutorials` (ref [5]): a
  VirtualBox/Vagrant VM prebuilt with **Mininet**, the **BMv2** (`simple_switch`)
  P4 software switch, the `p4c` compiler, and P4Runtime tooling.
- Traffic generator: **iPerf 3.7** (specific version).
- Congestion control under test: **TCP BBR** on all sender-side flows.

### 4.2 Network Topology (Fig. 2)

```
                                          round-trip delay 80 ms
                                     ┌───────────────────────────► Receiver1
Sender ── round-trip delay 0.0664ms ─┤ Switch (P4/BMv2)
                                     │        round-trip delay 40 ms
                                     ├───────────────────────────► Receiver2
                                     │
                                     │        round-trip delay 20 ms
                                     └───────────────────────────► Receiver3
```

- One Sender host, one P4 switch, three Receiver hosts (Receiver1/2/3).
- Sender↔Switch link: RTT ≈ 0.0664 ms (effectively negligible — Sender and Switch are
  "close").
- Switch↔Receiver1: RTT 80 ms (longest — the "elephant" RTT under the unfairness effect).
- Switch↔Receiver2: RTT 40 ms.
- Switch↔Receiver3: RTT 20 ms (shortest).
- Three simultaneous TCP BBR flows: Sender→Receiver1, Sender→Receiver2, Sender→Receiver3,
  all sharing the Sender–Switch link/the switch as the common bottleneck point.
- **Gap in the paper:** no explicit bottleneck bandwidth (link rate) is stated for the
  shared segment. A bottleneck must exist for BBR contention/unfairness to manifest; we
  will need to configure a rate limit (e.g., via Mininet `TCLink` `bw=` or `tc` token
  bucket) on the shared link and document our chosen value as an assumption, since the
  paper does not give it explicitly. See `docs/OBSERVATIONS.md`.

### 4.3 Timeline / Procedure
- Each run: iPerf3 traffic Sender→Receiver1, Receiver2, Receiver3, run **simultaneously**
  for **600 seconds**.
- QACK (static or dynamic, depending on scenario) is **enabled at ~300 s** (mid-run).
- Three scenarios compared:
  1. **w/o QACK** — no QACK at all (baseline BBR unfairness).
  2. **w/ QACK static method** — QACK always targets Receiver1 (80 ms / largest RTT).
  3. **w/ QACK dynamic method** — QACK target chosen dynamically per Section 3.

### 4.4 Parameters
| Parameter | Value |
|---|---|
| Congestion control | TCP BBR (all flows) |
| Traffic generator | iPerf 3.7 |
| Number of flows | 3 (Sender→Receiver1/2/3) |
| Run duration | 600 s |
| QACK enable time | ~300 s into the run |
| QACK interval | 1024 packets |
| Sender↔Switch RTT | 0.0664 ms |
| Switch↔Receiver1 RTT | 80 ms |
| Switch↔Receiver2 RTT | 40 ms |
| Switch↔Receiver3 RTT | 20 ms |
| Static QACK target | Receiver1 (largest RTT) |
| Dynamic QACK target | argmax(per-connection packet counter), re-evaluated every interval |
| Bottleneck bandwidth | **Not stated in paper — must be assumed/tuned; documented as a gap** |

### 4.5 Metrics
- **Throughput** per flow, in Mbit/s, over elapsed time (0–600 s).
- **Fairness Index** over time (0–1 scale). The paper does not name the formula, but the
  0–1 scale and "Fairness Index" terminology strongly indicate **Jain's Fairness Index**:
  `FI = (Σxi)^2 / (n × Σxi^2)` computed across the 3 flows' throughputs at each sampling
  point (standard in this exact research lineage — see ref [4], same last author). We will
  use Jain's index and flag this as an interpretation, not an explicit paper statement.
- **Average Fairness Index** per scenario (single summary number per bar in Fig. 3).

### 4.6 Evaluation Method
- Fig. 3: bar chart of **average** Fairness Index for the 3 scenarios (w/o QACK, static,
  dynamic) — one number per scenario.
- Figs. 4 & 5: time-series of per-flow throughput (3 lines: 80/40/20 ms) plus Fairness
  Index (secondary axis), across the full 600 s run, for the static method (Fig. 4) and
  dynamic method (Fig. 5) respectively — QACK switched on at ~300 s, so the plot shows
  before/after within a single run.

## 5. Figures / Tables That Must Be Reproduced

| Item | Type | Description |
|---|---|---|
| Fig. 1 | Diagram (conceptual) | QACK method behavior (normal vs QACK case) — recreate as an architecture/sequence diagram, not data-driven |
| Fig. 2 | Diagram (topology) | Network topology — recreate as Mininet/P4 topology script + diagram |
| Fig. 3 | Bar chart | Average Fairness Index, 3 bars: w/o QACK (~0.65), w/ static (~0.83), w/ dynamic (~0.93) — values are visual estimates from the PDF chart, not stated numerically in text |
| Fig. 4 | Line chart | Throughput trend, static method, 600 s, 3 flows + fairness index |
| Fig. 5 | Line chart | Throughput trend, dynamic method, 600 s, 3 flows + fairness index |

## 6. Hardware / Software Requirements

| Requirement | Paper's environment | Notes |
|---|---|---|
| OS | Linux (P4.org tutorial VM, Ubuntu-based) | Our host is **Windows 11** — needs a Linux layer (see Phase 4 decision) |
| Emulation | Mininet | Provides hosts + virtual links |
| Switch | BMv2 `simple_switch` (P4 software switch) | From `p4lang/tutorials` / `p4lang/behavioral-model` |
| P4 compiler | `p4c` | Compiles the per-connection-counter + QACK P4 program |
| Control plane | P4Runtime (Python) | Reads counters, resets them, triggers QACK send/target logic |
| Congestion control | TCP BBR | Requires Linux kernel ≥ 4.9 with `tcp_bbr` module available |
| Traffic generator | iPerf 3.7 (exact version) | Must pin this version for fidelity |
| Link delay emulation | netem (`tc qdisc`) via Mininet `TCLink` | To realize 0.0664/20/40/80 ms RTTs |
| QACK packet crafting | Not detailed in this paper (belongs to ref [3], unpublished/inaccessible to us) | **Known gap** — we must design a reasonable equivalent (see `docs/OBSERVATIONS.md`) |

## 7. Known Gaps / Ambiguities (to resolve or document as limitations)

1. **Bottleneck bandwidth** of the shared link is never stated numerically.
2. **QACK packet construction** internals (how the switch forges a valid spoofed TCP ACK —
   sequence/ack numbers, retransmission/robustness handling) are described only at a
   conceptual level here; full detail lives in the referenced-but-inaccessible prior paper
   [3] ("submitted for IEEE HPSR CTN-SRMI 2025").
2b. Whether the QACK interval (1024 packets) is counted **globally** across all
    candidate connections combined, or **per connection**, is not fully explicit; the
    wording ("counts the number of packets forwarded by the switch in each connection...
    each counter is reset to 0") reads most naturally as: a single global trigger every
    1024 forwarded packets, at which point the argmax-counter connection is targeted and
    **all** counters reset. We will implement this interpretation and document it.
3. **Fairness Index formula** is assumed to be Jain's Fairness Index (not stated
   explicitly, inferred from convention and prior work by the same authors).
4. **Exact numeric values** in Figs. 3/4/5 are only available as pixel/visual estimates
   from the chart images — no data tables are published.
5. Our replication host is **Windows**, not the Linux/P4.org VM used in the paper — see
   Phase 4 for the environment-equivalence decision.

These will each get an entry in `docs/OBSERVATIONS.md` as they're encountered/resolved,
and any place our replicated setup diverges from the paper will be logged there and in
`docs/RESULTS.md`.

## 7b. P4 / Controller Architecture Decision (our design, filling gap #2)

The paper does not publish how the switch constructs a valid spoofed ACK (that
belongs to its unpublished prior paper, ref [3]). We designed the following
concrete mechanism, chosen to be implementable in BMv2 + P4Runtime and to match
the paper's *observable* behavior (per-connection packet counting in the data
plane; QACK sent to the argmax connection every 1024 packets; all counters reset):

- **Data plane (P4_16, `v1model`, BMv2 `simple_switch_grpc`):**
  - L2/L3 forwarding for the 4 hosts (Sender, Receiver1/2/3) through the single
    switch.
  - A register array indexed by a hash of the 5-tuple, one slot per candidate
    connection (3 candidates: Sender→Receiver1/2/3 — the candidate set is
    static/known, matching "all passing connections that are candidates are
    given statically" in the paper), storing a **per-connection forwarded-packet
    counter**.
  - A second small register (or one field per connection slot) storing the
    **last-observed TCP timestamp option value (TSval)** and the current
    cumulative **ack number** (highest contiguous byte offset seen) for that
    connection — needed to construct a QACK that a real Linux TCP stack will
    accept as a legitimate, RTT-sample-producing ACK.
  - A single global counter of total forwarded TCP data packets across all
    candidates. When it reaches the **QACK interval (1024)**, the data plane
    sends a **digest** to the controller with a snapshot of all per-connection
    counters, then the global counter (and, once the controller replies, the
    per-connection counters) are reset to 0.
- **Control plane (Python, P4Runtime):**
  - Static method: always selects the pre-configured target connection
    (Receiver1 / 80 ms), ignoring the digest's counter values.
  - Dynamic method: on each digest, computes **argmax** over the per-connection
    counters and selects that connection as the QACK target.
  - Crafts the QACK packet (Scapy): source = target receiver's IP:port,
    destination = sender's IP:port, TCP flags = ACK, ack number = the tracked
    cumulative byte offset, **TCP timestamp option TSecr = the last-observed
    TSval for that connection** (this is what makes a real Linux BBR sender
    compute a tiny RTT sample — it reflects the timestamp instantly instead of
    after a full end-to-end round trip; TCP timestamps are on by default in
    modern Linux, `net.ipv4.tcp_timestamps=1`).
  - Injects the QACK via a **P4Runtime PacketOut** through the switch's CPU
    port, so the packet genuinely originates from "the network element," matching
    Fig. 1(b) in the paper.
  - Resets the data-plane per-connection registers after acting on each digest.

This is **our own reconstruction**, not a verified match to the authors' actual
QACK implementation — flagged per `docs/OBSERVATIONS.md` item 2. It will be
revisited if measured behavior doesn't resemble Figs. 4/5.

---

## 8. Replication Roadmap (7 Phases)

### Phase 1 — Read and understand the paper ✅ COMPLETE
- Full text + all figures read and transcribed above.

### Phase 2 — Extract complete experimental methodology ✅ COMPLETE
- Sections 1–7 above.

### Phase 3 — Create the replication roadmap ✅ COMPLETE (this section)
- See detailed task breakdown in `docs/REPLICATION_CHECKLIST.md`.

### Phase 4 — Prepare the replication environment ⏳ NEXT
Decisions and setup required:
- Choose Linux execution environment for Windows host (WSL2 / VirtualBox+Vagrant
  p4lang tutorial VM / Docker / cloud VM) — **requires user decision**, logged as a
  pending question.
- Install Mininet, BMv2 (`simple_switch`), `p4c`, P4Runtime Python bindings.
- Verify TCP BBR is available (`modprobe tcp_bbr`, `sysctl net.ipv4.tcp_available_congestion_control`).
- Install iPerf **3.7** exactly.
- Build Mininet topology script matching Fig. 2 (delays, and an assumed bottleneck
  bandwidth, documented).
- Write baseline P4 program (L2/L3 forwarding + per-connection register counters).

### Phase 5 — Replicate every experiment
- Experiment A: baseline, no QACK (600 s, 3 flows).
- Experiment B: QACK static method (target = Receiver1), 600 s, QACK on at 300 s.
- Experiment C: QACK dynamic method, 600 s, QACK on at 300 s.
- Each experiment repeated as needed for stable results; all raw iPerf/tcpdump logs
  saved to `outputs/`, all commands logged to `docs/COMMAND_HISTORY.md`, each run
  logged to `docs/EXPERIMENT_LOG.md`.

### Phase 6 — Compare obtained results with the paper
- Reproduce Fig. 3 (bar chart), Fig. 4 (static time series), Fig. 5 (dynamic time
  series) from our own measured data.
- Side-by-side comparison table in `docs/RESULTS.md` (paper's visual-estimate values
  vs our measured values), with commentary on any deviation and likely cause
  (referencing the gaps in Section 7 above).

### Phase 7 — Prepare the final recording guide
- `docs/RECORDING_GUIDE.md` filled in with a step-by-step script for recording a
  demonstration of the replicated experiments and results walkthrough.

---
*Last updated: 2026-08-01 (Phase 1–3 complete).*
