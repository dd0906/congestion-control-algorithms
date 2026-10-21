# Results — Paper vs Replication

**Read this alongside `docs/OBSERVATIONS.md` item 9** — under a hard 1-hour project
deadline, the full P4/BMv2/Mininet toolchain build could not finish in time, so this
replication was executed with a **fast-path substitute environment** (Linux network
namespaces + veth + tc netem/tbf instead of Mininet/BMv2; a Scapy raw-socket proxy
instead of a compiled P4 program) and **scaled-down run durations** (120s per
scenario, QACK enabled at t=60s, instead of the paper's 600s/QACK-at-300s). These are
real, executed experiments with real measured data — not simulated or fabricated —
but they are not a like-for-like toolchain match to the paper, and the numbers below
should be read as directional/qualitative validation, not precise reproduction.

## 1. Fairness Index summary (cf. Fig. 3)

| Scenario | Paper (visual estimate) | Our replication (post-QACK-enable window) | Delta |
|---|---|---|---|
| w/o QACK | ~0.65 | **0.612** (full 120s run) | close, slightly lower |
| w/ QACK static method | ~0.83 | **0.637** | much smaller improvement than paper |
| w/ QACK dynamic method | ~0.93 | **0.635** | much smaller improvement than paper; **not better than static in our data** |

Our replicated bar chart: `outputs/fig3_replication.png`. Raw summaries:
`outputs/no_qack_summary.json`, `outputs/qack_static_summary.json`,
`outputs/qack_dynamic_summary.json`.

**Honest assessment:** the *direction* of the baseline unfairness is confirmed (see
section 2), and QACK-static visibly perturbs the throttled flow's throughput (section
3), but the magnitude of fairness improvement in our data is far smaller than the
paper's, and — unlike the paper — our dynamic method did not measurably outperform
the static method within the compressed 60s post-enable window.

**Verified root cause (confirmed by reading both full QACK proxy logs,
`outputs/qack_static_qack.log` and `outputs/qack_dynamic_qack.log`, in full — not
just their tails):** in this executed run, the dynamic method's argmax logic
selected connection 0 (the 80ms flow) in **all 35 out of 35** fired QACKs — the
exact same target, the exact same number of times, as the static method. Connection
0 legitimately had the highest per-window packet count every single round, so
"dynamic" and "static" targeting were **not actually different treatments in this
run** — they degenerated to the identical target sequence. Despite that, the
*effect* differed sharply: in the static run, connection 0's packet share
collapsed from ~650-690/window down to ~80-150/window by the end; in the dynamic
run, connection 0's share never dropped below ~540/window the entire time. Since
the target and QACK count were identical, this difference must come from
elsewhere — most plausibly:
1. **Run-to-run stochastic variance.** The two runs are independent 120s
   executions with their own BBR probe-cycle timing and kernel scheduling: nothing
   pairs them, so two runs targeting the same connection the same number of times
   can still land QACKs at different points in each connection's BBR cycle and
   produce different outcomes purely by chance.
2. **Simplified QACK packet crafting** (`scripts/qack_proxy.py`) reuses the last
   *genuinely observed* receiver seq/timestamp rather than synthesizing values, so
   an unknown fraction of injected QACKs are likely silently dropped by the
   sender's TCP PAWS check (see the file's docstring) — how many of the 35 actually
   "landed" is not directly measured, and could easily differ between the two runs.
3. **60s post-enable window is short** relative to the paper's 300s, leaving little
   margin for a weaker-landing sequence of QACKs to still show a visible effect.
4. **Bottleneck emulation is a single best-effort `tbf`**, not whatever AQM/queueing
   the paper's real environment used — queueing behavior strongly affects BBR
   fairness dynamics.
5. **Environment substitution itself** (netns/veth/tc vs. Mininet/BMv2/P4Runtime) —
   see `docs/OBSERVATIONS.md` item 9 for the full list of consequent differences.

This is reported as-is rather than adjusted to look more favorable. A follow-up with
longer run durations and/or the original P4/BMv2 toolchain (started but not finished
— see item 9) would be needed to check whether the dynamic-vs-static gap the paper
reports appears over a longer horizon.

**Additional honest observation (added after visual review of all three charts
side by side):** all three scenarios — including the no-QACK baseline — show the
same recurring sawtooth oscillation pattern for roughly the first 85-90 seconds of
their run (throughput repeatedly cycling down to near-0 and back up across all
three flows). Since this appears in the baseline too, it is almost certainly an
artifact of the single-FIFO `tbf` bottleneck emulation (periodic queue starvation),
**not** an effect of QACK. A direct consequence: the static method's visible
throttling effect only becomes apparent in the *last* ~25 seconds of its 120s run
(from roughly t=95s onward) — i.e., about 35 seconds after QACK was actually
enabled at t=60s — not immediately at the enable point. This is consistent with
BBR's RTprop hold time plus the QACK proxy needing to accumulate enough packets to
fire, and combined with the verified finding above (identical target, identical
QACK count, different outcome), it points squarely at causes 1-3 above — run-to-run
variance and/or QACK-delivery-fidelity differences between the two independent
runs — rather than any actual difference in *how* the static and dynamic
algorithms behaved in this particular pair of runs.

## 2. Baseline RTT-unfairness (qualitative check against the paper's core claim)

Confirmed: in `outputs/no_qack_timeseries.csv`, the 80ms-RTT flow steady-state
throughput (~10.5 Mbit/s) is roughly **3x** the 40ms flow (~3.65 Mbit/s) and the
20ms flow (~3.1 Mbit/s) once BBR converges — i.e., the **longest-RTT connection
dominates the bottleneck**, exactly the direction of unfairness the paper (and its
ref [2], Hock et al.) describes. This is the one result that reproduces cleanly.

## 3. Throughput trend — static method (cf. Fig. 4)

`outputs/qack_static_throughput.png`, data in `outputs/qack_static_timeseries.csv`.
The proxy log (`outputs/qack_static_qack.log`) shows a clear, real progression: in
the first several 1024-packet windows after QACK is enabled, the targeted 80ms
connection carries ~650-690 packets per window vs. ~130-210 for the other two
(matching the pre-QACK imbalance); by the last several windows this **inverts** —
the 80ms connection drops to ~80-150 packets/window while the 40ms connection rises
to ~600-660. This qualitatively matches the paper's own description of the static
method's failure mode ("the throughput of the largest RTT decreased remarkably...
in some periods it was the lowest of the three"). The throughput time series shows
the 80ms flow oscillating between ~0 and ~10-11 Mbit/s in the back half of the run,
consistent with this.

## 4. Throughput trend — dynamic method (cf. Fig. 5)

`outputs/qack_dynamic_throughput.png`, data in `outputs/qack_dynamic_timeseries.csv`.
Unlike the static run, the tail-end throughput values (80ms ~10.5, 40ms ~3.65, 20ms
~3.1 Mbit/s) are close to the **no-QACK baseline's** tail values — i.e., in our
replication the dynamic method's effect on steady-state throughput share is much
less visible than the static method's, which is the opposite emphasis from the
paper's claim that dynamic "avoided too much reduction" while still improving
fairness more than static. Notably, this is **not** because the dynamic method
targeted a different connection or fired fewer QACKs — `outputs/qack_dynamic_qack.log`
shows it targeted connection 0 (the 80ms flow) in all 35 of 35 fired QACKs,
identical to the static run — see the verified root-cause discussion in section 1.
The weaker visible effect despite an identical target/count is most likely
run-to-run variance and/or QACK-delivery fidelity, not a difference in the
targeting algorithm itself in this particular pair of runs.

## 5. Overall Assessment

- **Confirmed:** baseline TCP BBR RTT unfairness (longest-RTT flow dominates) —
  the paper's foundational premise.
- **Qualitatively confirmed:** QACK-style RTT-spoofing measurably shifts bandwidth
  share away from a targeted connection, and a *statically*-targeted approach can
  overshoot and make the target the new underdog — matching the paper's own
  critique of the static method that motivates its proposed dynamic method.
- **Not confirmed within this fast-path, time-boxed replication:** that the
  *dynamic* targeting method improves fairness beyond the static method. Our data
  shows the opposite emphasis, most plausibly because of the compressed timescale
  and simplified QACK-crafting logic documented above and in
  `docs/OBSERVATIONS.md` item 9 — not treated here as evidence against the paper's
  claim, just as a limitation of this particular fast replication that a longer/
  higher-fidelity re-run should revisit.

---
*Last updated: 2026-08-01, after executing all three scenarios under the 1-hour
deadline via the fast-path netns/tc/Scapy environment.*
