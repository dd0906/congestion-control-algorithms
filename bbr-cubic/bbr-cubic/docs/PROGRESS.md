# Progress Tracker

**Overall Progress: ~97%.** All experiment/analysis/documentation work is complete
and verified. The **only** thing left is recording the actual demo video — everything
needed to do that (exact commands, exact narration, verified file references) is
already written and tested. See `docs/RESUME_HERE.md` if you are picking this project
up fresh with no prior context.

## Phase Status
| Phase | Status | % of phase complete |
|---|---|---|
| 1. Read and understand the paper | ✅ Complete | 100% |
| 2. Extract experimental methodology | ✅ Complete | 100% |
| 3. Create replication roadmap | ✅ Complete | 100% |
| 4. Prepare replication environment | ✅ Complete (fast-path substitute) | 100% |
| 5. Replicate every experiment | ✅ Complete (3 real runs, scaled duration) | 100% |
| 6. Compare results with paper | ✅ Complete, including a verified root-cause finding | 100% |
| 7. Prepare final recording package | ✅ Commands + narration tested and finalized | 100% (recording itself not done) |

## Why "fast-path substitute" instead of the original toolchain
Under a hard 1-hour deadline, the from-source P4/BMv2/Mininet build (protobuf, gRPC,
PI, BMv2, p4c) could not finish in time. Phase 4 pivoted to Linux network namespaces
+ veth + tc (netem/tbf) for the topology and a Scapy raw-socket proxy for the QACK
mechanism, with run durations scaled from 600s to 120s per scenario (QACK enabled at
the midpoint, t=60s instead of t=300s). Every deviation is documented in
`docs/OBSERVATIONS.md` (item 9) and `docs/FINAL_STATE.md`. This is real, executed,
measured data, not simulated — see `docs/RESULTS.md` for the full numeric comparison.

## What's 100% Done
- Paper read, methodology extracted, roadmap built (`docs/PROJECT_PLAN.md`).
- Environment provisioned: dedicated `FairFlow-Ubuntu2204` WSL2 distro (Ubuntu
  22.04.5 LTS, root user), BBR loadable, iperf3 + Scapy working.
- P4/BMv2 path started (`scripts/qack.p4`, controller design in
  `docs/PROJECT_PLAN.md` section 7b) but not finished — preserved, untouched, for
  an optional future higher-fidelity re-run (partial build tree left in
  `FairFlow-Ubuntu2204:/root/p4-tools`).
- Fast-path topology (`scripts/netns_topo.sh`) and QACK proxy
  (`scripts/qack_proxy.py`, static + dynamic modes) built and verified working.
- **All 3 experiments actually executed** (`scripts/run_scenario.sh`): baseline
  (`no_qack`), QACK-static (`qack_static`), QACK-dynamic (`qack_dynamic`) — real
  TCP BBR / iperf3 traffic, real measured throughput, real QACK packets injected.
  Full detail in `docs/EXPERIMENT_LOG.md`.
- Analysis run on the real data (`scripts/analyze_results.py`, `scripts/make_fig3.py`):
  Jain's Fairness Index time series, Fig. 3/4/5-equivalent charts, all saved in
  `outputs/`.
- Full, honest comparison against the paper in `docs/RESULTS.md`, **including a
  verified root-cause finding**: in the executed runs, the dynamic method's argmax
  logic selected the same connection, the same number of times (35/35), as the
  static method — so the weaker observed effect in the dynamic run is not because
  it "targeted the wrong flow," but most likely run-to-run variance and/or
  QACK-delivery fidelity between the two independent runs. This was discovered by
  reading the full `qack_dynamic_qack.log` (not just its tail) during final review,
  and an earlier draft narration that incorrectly said dynamic "switches targets"
  has been corrected everywhere it appeared.
- All output artifacts (9 raw iperf3 JSONs, 3 summary JSONs, 3 timeseries CSVs, 4
  PNG charts, 2 QACK proxy logs) verified twice, read-only, via
  `scripts/verify_outputs.py` — most recently immediately before finalizing the
  handoff package below. All checks passed both times. No experiment was ever rerun.
- **Final handoff package written** for recording without further AI/human
  assistance: `docs/FINAL_STATE.md` (complete experiment writeup),
  `docs/RECORDING_COMMANDS.md` (every command, tested, exact), `docs/RECORDING_SCRIPT.md`
  (narration only), `docs/FILE_INDEX.md` (what every file is), `docs/RESUME_HERE.md`
  (orientation for a future AI session with zero context). `docs/RECORDING_GUIDE.md`
  is an earlier, superseded draft — kept for history, but `RECORDING_COMMANDS.md` +
  `RECORDING_SCRIPT.md` are the authoritative ones to use for the actual recording.

## What's Left
- **Record the actual demo video.** Nothing further needs to be built, run, or
  changed — follow `docs/RECORDING_COMMANDS.md` (commands) alongside
  `docs/RECORDING_SCRIPT.md` (what to say) exactly as written.

## Optional, Not Required
- A higher-fidelity re-run using the original P4/BMv2/Mininet toolchain (started,
  not finished — see `docs/OBSERVATIONS.md` item 9 and `docs/RESUME_HERE.md` for how
  to resume it) at the paper's full 600s/300s-enable duration.

---
*Last updated: 2026-08-01. All experiment, analysis, and documentation work is
complete and re-verified; only the video recording itself remains.*
