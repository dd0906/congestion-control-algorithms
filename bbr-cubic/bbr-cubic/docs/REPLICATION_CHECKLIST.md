# Replication Checklist

Legend: `[x]` done · `[ ]` pending · `[~]` blocked/needs decision

## Phase 1 — Read and understand the paper
- [x] Obtain and fully read the paper PDF (all pages, all figures, all references)
- [x] Identify prior-work dependencies (ref [2] Hock et al. unfairness finding; ref [3]
      QACK mechanism, authors' own unpublished/submitted paper)

## Phase 2 — Extract complete experimental methodology
- [x] Problem Statement
- [x] Experimental Setup
- [x] Network Topology
- [x] Hardware/Software Requirements
- [x] Algorithms Used (QACK mechanism + dynamic target selection)
- [x] Parameters (QACK interval, RTTs, duration, enable time)
- [x] Metrics (Throughput, Fairness Index)
- [x] Evaluation Method (3-scenario comparison, bar chart + time series)
- [x] Figures/Tables to reproduce (Fig. 1–5)
- [x] Document ambiguities/gaps (bottleneck bandwidth, QACK packet crafting detail,
      fairness formula, interval semantics)

## Phase 3 — Create the replication roadmap
- [x] Write `docs/PROJECT_PLAN.md` with full roadmap
- [x] Write this checklist

## Phase 4 — Prepare the replication environment
- [x] User chose WSL2 as the execution environment
- [x] Minimal, wildcard-free passwordless sudo configured and verified
- [x] Dedicated `FairFlow-Ubuntu2204` distro provisioned (non-interactive `wsl --import`)
- [x] TCP BBR confirmed loadable (`modprobe tcp_bbr`)
- [x] iPerf3 confirmed present; Scapy installed
- [~] Mininet / BMv2 / p4c / P4Runtime — build started, **not completed** (killed
      under the 1-hour deadline; see `docs/OBSERVATIONS.md` item 9). Partially-built
      tree preserved in `FairFlow-Ubuntu2204:/root/p4-tools` for optional resumption.
- [x] **Fast-path substitute environment built instead**: `scripts/netns_topo.sh`
      (netns + veth + tc netem/tbf), verified with ping RTT checks and a smoke test
- [x] Bottleneck bandwidth assumption documented (15 Mbit/s, `docs/OBSERVATIONS.md` item 1)
- [x] `scripts/qack.p4` written (P4 design, not compiled — held for future re-run)
- [x] `scripts/qack_proxy.py` written (fast-path QACK: static + dynamic modes)
- [x] Smoke-test run (10s, no QACK) confirmed unfair throughput split in the
      expected direction (longest RTT dominates)

## Phase 5 — Replicate every experiment
- [x] Experiment A — baseline, w/o QACK, **120 s** (scaled from 600s), 3 flows
- [x] Experiment B — w/ QACK static method (target = 80 ms / Receiver1), QACK on at
      t=60s (scaled from 300s), 120 s total
- [x] Experiment C — w/ QACK dynamic method, QACK on at t=60s, 120 s total
- [x] Raw iPerf3 JSON logs saved to `outputs/`
- [x] QACK proxy logs (showing every fired QACK + counters) saved to `outputs/`
- [x] Every command logged to `docs/COMMAND_HISTORY.md`
- [x] Every run's conditions/results logged to `docs/EXPERIMENT_LOG.md`
- [ ] Screenshots not captured (text/log-based verification used instead; optional
      follow-up per `docs/RECORDING_GUIDE.md`)
- [x] No anomalous runs — all 3 completed cleanly on first attempt after the smoke test

## Phase 6 — Compare obtained results with the paper
- [x] Jain's Fairness Index computed per scenario from real measured throughputs
- [x] Fig. 3 equivalent (bar chart) reproduced from our data → `outputs/fig3_replication.png`
- [x] Fig. 4 equivalent (static method time series) → `outputs/qack_static_throughput.png`
- [x] Fig. 5 equivalent (dynamic method time series) → `outputs/qack_dynamic_throughput.png`
- [x] Side-by-side comparison table (paper visual-estimate vs our numbers) in `docs/RESULTS.md`
- [x] Honest analysis of deviations and likely causes written in `docs/RESULTS.md` /
      `docs/OBSERVATIONS.md` — including the divergence where our dynamic method did
      not outperform static (unlike the paper)

## Phase 7 — Prepare the final recording guide
- [x] `docs/RECORDING_GUIDE.md` filled in with a concrete, step-by-step demonstration
      script referencing the actual files/commands produced
- [x] What to show on screen identified for each step
- [x] Screenshot/recording destinations noted
- [ ] Actual video recording not made (guide is ready; recording itself is a
      separate optional user action, not part of the 1-hour deliverable)

---
*This checklist is updated alongside `docs/PROGRESS.md` at every milestone. `[~]`
marks an item that was started but deliberately not completed, with the reason
documented in `docs/OBSERVATIONS.md`.*
