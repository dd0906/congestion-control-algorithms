# Experiment Detail

## Topology (`scripts/topo.sh`)
```
senderA (BBR)   --fast link--\
                               switch --BOTTLENECK (rate+delay)-- receiver
senderB (CUBIC) --fast link--/
```
4 Linux network namespaces: `senderA`, `senderB`, `switch`, `receiver`. senderA and
senderB each connect to `switch` over an unconstrained veth link; `switch` connects
to `receiver` over the single link where the bottleneck (rate limit + delay) is
applied — this is the **shared constrained bottleneck** both flows compete for.
IP forwarding enabled on `switch`. Same netns/veth/tc technique as the parent
project's QACK replication (`../scripts/netns_topo.sh`), reused directly.

Round-trip delay is split evenly across both ends of the switch-receiver link
(same convention as the QACK replication); bandwidth is rate-limited via `tc tbf`
on both ends of that same link.

## Congestion control verification (not inferred from flags)
`iperf3 -C bbr` / `-C cubic` sets the requested algorithm via `setsockopt`, but to
**verify** it was actually applied, `scripts/run_condition.sh` runs `ss -ti` inside
each sender's network namespace ~3 seconds into every run, capturing the kernel's
own live TCP socket state. Saved to `outputs/<label>_bbr_ss.log` /
`outputs/<label>_cubic_ss.log`. Each shows two connections per sender: iperf3's
small control channel (frequently shows `cubic`, the system default, regardless of
the `-C` flag — this is expected, the control channel isn't the measured data
flow) and the actual **data-transfer connection** (identifiable by non-trivial
`bytes_sent`/`segs_out`), which shows `bbr` for senderA and `cubic` for senderB in
every run — confirmed by direct inspection, not assumed.

## Scenarios executed (all real, all actually run)

| # | Label | Mode | Rate | Delay | Duration |
|---|---|---|---|---|---|
| 1 | `solo_bbr` | BBR alone | 10 Mbit/s | 20ms | 20s |
| 2 | `solo_cubic` | CUBIC alone | 10 Mbit/s | 20ms | 20s |
| 3 | `conditionA` | BBR + CUBIC coexisting | 10 Mbit/s | 20ms | 30s |
| 4 | `conditionB` | BBR + CUBIC coexisting | 5 Mbit/s | 50ms | 30s |

Exact commands (all via `scripts/run_condition.sh <label> <rate_mbit> <delay_ms>
<mode> <duration_s> <outdir>`, one continuous process per run — required, since
separate `wsl -d ...` invocations don't reliably share netns state, a finding
carried over from the parent QACK replication):
```
run_condition.sh solo_bbr    10 20 solo_bbr  20 outputs
run_condition.sh solo_cubic  10 20 solo_cubic 20 outputs
run_condition.sh conditionA  10 20 coexist   30 outputs
run_condition.sh conditionB  5  50 coexist   30 outputs
```

A short 8-second `smoketest` coexistence run (present in `outputs/` as
`smoketest_*`) was run first to validate the pipeline before the 4 real runs
above — not otherwise analyzed, not part of the reported results.

## Note on "delay" convention
"20 ms delay" / "50 ms delay" are treated as **round-trip** figures (matching the
convention already established in the parent QACK replication), implemented as
delay/2 applied at each end of the bottleneck link.

## Metrics computed (`scripts/analyze.py`, read-only against `outputs/`)
- Per-second throughput per flow, from real iperf3 `-J` JSON output.
- **Jain's Fairness Index** across the 2 flows at each sample and averaged, for
  the two coexistence conditions.
- **Retransmits** (sender-side, TCP), read directly from iperf3's own
  `end.sum_sent.retransmits` field — real measured values, not estimated.

## Deviation from the suggested example conditions
None needed — Condition A (10 Mbit/s, 20ms) and Condition B (5 Mbit/s, 50ms) were
used exactly as suggested; the environment supported both without modification.


