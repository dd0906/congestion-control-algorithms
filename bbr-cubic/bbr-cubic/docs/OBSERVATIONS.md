# Observations, Deviations & Limitations

This file tracks anything where our replication diverges from the paper — either
because the paper is ambiguous/under-specified, or because of hardware/software
limitations on our side — along with the closest-equivalent approach we chose instead.
Per the project rules, nothing here should be silently "fixed" without a note.

## Logged from Phase 1–3 (paper reading)

1. **Bottleneck bandwidth not stated.** The paper's Fig. 2 gives only RTTs
   (0.0664/80/40/20 ms), not a link rate for the shared bottleneck. Without a rate
   limit, three BBR flows over Mininet's default (near-infinite, host-CPU-bound)
   link capacity may not create a meaningful bottleneck at all. **Planned approach:**
   choose a bottleneck bandwidth on the Sender–Switch (or Switch-side aggregate) link
   in Phase 4, sized so combined BBR flow demand exceeds it (creating real
   contention), and record the exact value here once chosen, with rationale.

2. **QACK packet crafting is under-specified.** The mechanics of how the switch
   forges a spoofed ACK that a real Linux BBR sender will accept (valid sequence
   number tracking, TCP/IP checksum, source spoofing of the receiver's IP:port) are
   detailed in the authors' prior paper [3] ("Control TCP BBR Throughput in a
   Programmable Switch," submitted to IEEE HPSR CTN-SRMI 2025), which is **not
   publicly available to us**. **Planned approach:** design our own P4/control-plane
   implementation that achieves the same effect (switch-generated ACK with a
   spoofed source causing the sender to sample a much smaller RTT), and document
   the exact mechanism we use here once built, flagged clearly as "our
   interpretation," not a verified match to the original.

3. **Fairness Index formula assumed = Jain's Fairness Index.** Not stated
   explicitly in the paper; inferred from the 0–1 scale, the term "Fairness Index",
   and the same research group's prior published work (ref [4]) which uses this
   convention.

4. **QACK interval trigger semantics assumed global, not per-connection.** "The
   prototype implementation counts the number of packets forwarded by the switch in
   each connection. When a QACK is applied, the QACK packet is sent to the sender of
   the connection with the largest counter, and each counter is reset to 0." We read
   this as: one global counter of total forwarded packets triggers a QACK event
   every 1024 packets; at that event, the argmax per-connection counter is targeted
   and *all* per-connection counters reset to 0. This will be revisited if the
   replicated fairness curves don't resemble Figs. 4/5 in shape.

5. **Exact numeric values in Figs. 3/4/5 are visual estimates only** — no data
   tables are published in the paper. Our Phase 6 comparison will necessarily be
   qualitative-shape + approximate-magnitude, not exact-number matching.

6. **Host environment mismatch — resolved.** The paper used VMs from P4.org (p4lang
   tutorials — Mininet + BMv2 + P4Runtime on Linux). Our host is Windows 11. User
   chose **WSL2 (Ubuntu)** as the equivalence approach (2026-08-01).

7. **Toolchain-installer OS compatibility — resolved via dedicated second distro.**
   The Windows machine's existing default WSL distro is Ubuntu **26.04** (very new).
   The most practical P4 dev-environment installer available
   (`nsg-ethz/p4-utils install-p4-dev.sh`, which builds pinned 2023-era
   protobuf 3.20.3 / gRPC 1.44.0 / PI / BMv2 / p4c from source) has a **hard
   version gate and is only tested on Ubuntu 20.04/22.04** — running it against
   26.04 risked hours of toolchain-incompatibility debugging (newer GCC/OpenSSL/
   Python breaking old build scripts) with no guarantee of success.
   **Closest-equivalent approach taken:** provisioned a second, dedicated WSL2
   distro, `FairFlow-Ubuntu2204`, via `wsl --import` of Canonical's official
   Ubuntu 22.04 WSL rootfs tarball (`cloud-images.ubuntu.com/wsl/jammy/current/...`)
   into `C:\WSL\FairFlow-Ubuntu2204`. This is non-interactive (no OOBE username/
   password prompt, unlike `wsl --install`) and leaves the existing default
   Ubuntu 26.04 distro completely untouched. The imported distro's only user is
   **root** (standard for `wsl --import`'d cloud rootfs images with no OOBE), so
   inside this dedicated distro there is no sudo/password friction at all — it is
   a single-purpose, isolated sandbox for this project only, not a shared
   general-purpose machine, which is why running as root there is acceptable.
   All Phase 4+ Linux-side work (Mininet, BMv2, p4c, P4Runtime, TCP BBR, iPerf 3.7,
   the experiments themselves) happens inside **`FairFlow-Ubuntu2204`**, not the
   original default Ubuntu distro. The passwordless-sudo scope set up earlier
   (`/etc/sudoers.d/fairflow-minimal` on the original Ubuntu/"praveena" distro) is
   consequently unused for the actual experiment run, but is left in place
   (harmless, minimal, already validated) in case that distro is used again.

8. **install-p4-dev.sh needed patching for package-name drift on this later
   Ubuntu 22.04 point release (22.04.5).** First run failed during the initial
   dependency install with two errors: (a) `libgc1c2` has no installation
   candidate — it was renamed to `libgc1` upstream since the installer script
   was last updated; (b) `linux-headers-$(uname -r)` doesn't exist for a WSL2
   kernel (`6.18.33.1-microsoft-standard-WSL2`), because the WSL2 kernel is
   built and distributed by Microsoft, not as an Ubuntu apt package — this
   dependency is only needed for building out-of-tree kernel modules, which
   this replication does not do. **Fix applied** (`scripts/patch_install_script.py`):
   substituted `libgc1` for `libgc1c2`, removed the `linux-headers-$KERNEL`
   line entirely, and set `FRROUTING=false` / `DOCUMENTATION=false` in the
   script's config (FRRouting is a routing-protocol suite and Sphinx docs
   generation are both irrelevant to this replication's topology — a single
   P4 switch doing static/L3 forwarding, no dynamic routing — so skipping them
   reduces build time and risk with no loss of fidelity to the paper). All
   remaining apt package lists in the script (PI deps, p4c deps, global setup)
   were pre-flight-checked with `apt-get install -s` (simulate) after the fix
   and confirmed installable before re-running the full build.

9. **Pivoted away from P4/BMv2/Mininet entirely under a hard 1-hour deadline.**
   After patching and restarting `install-p4-dev.sh`, the build was still in the
   gRPC clone/build stage roughly 20+ minutes in, with PI, BMv2, p4c, and Mininet
   builds still ahead of it — not realistically finishable in time to also leave
   room for writing the controller, running 3x 600s experiments (1800s of pure
   traffic time alone), analysis, and the recording guide within a 1-hour total
   budget. Per explicit instruction to prioritize a *working, reproducible*
   replication over exact toolchain matching, the environment was changed to a
   **fast-path substitute**, entirely in the already-provisioned
   `FairFlow-Ubuntu2204` distro:
   - **Topology** (`scripts/netns_topo.sh`): Linux network namespaces (`ip netns`)
     + veth pairs + `tc netem` (RTT delay) + `tc tbf` (bottleneck bandwidth),
     instead of Mininet + BMv2. Same logical topology as Fig. 2 (one "switch"
     namespace, one "sender", three "receivers" at 80/40/20ms RTT), same assumed
     15 Mbit/s bottleneck as previously logged in item 1.
   - **QACK mechanism** (`scripts/qack_proxy.py`): a Scapy raw-socket process
     running inside the "switch" namespace — sniffs the sender-facing interface,
     keeps the same per-connection packet counters and 1024-packet interval
     trigger as the P4 design in `scripts/qack.p4`/section 7b of
     `docs/PROJECT_PLAN.md`, and injects a spoofed ACK using TCP timestamp-echo,
     instead of a compiled P4 data-plane program + P4Runtime controller.
     `scripts/qack.p4` and the P4Runtime controller design are left in place,
     unused for this run, as the basis for a higher-fidelity re-run later.
   - **Run duration scaled down**: 120s per scenario with QACK enabled at t=60s,
     instead of the paper's 600s with QACK enabled at t=300s. Same 1024-packet
     QACK interval preserved unchanged (it's packet-count-based, not time-based,
     so no scaling was needed there).
   - The original `install-p4-dev.sh` build was killed (not deleted — the
     partially-built `/root/p4-tools` tree and the distro itself are left intact
     in `FairFlow-Ubuntu2204` in case a full-fidelity re-run is wanted later).
   - **Operational discovery**: separate `wsl -d <distro> -- <cmd>` invocations
     were found to NOT reliably share netns/veth/tc runtime state — a topology
     brought `up` in one invocation was gone (namespaces not found) by the next
     invocation, most likely because the WSL2 instance recycles when no process
     keeps it busy between separate command invocations. Fix: `scripts/run_scenario.sh`
     does topology-up, traffic generation, QACK proxy, and teardown **all within
     one continuous script/process/invocation** — this is required, not optional,
     for this fast-path approach to work at all.
   - **Known correctness simplification** in `qack_proxy.py`: the spoofed QACK's
     own TCP sequence number and TCP-timestamp "TSval" are set to the last
     *genuinely observed* values from that connection's real reverse-direction
     ACKs (not synthesized/predicted), to avoid a worse failure mode (desyncing
     the sender's PAWS-protection state with a fabricated, possibly out-of-range
     timestamp, which could cause the sender to start silently dropping the
     *real* receiver's subsequent legitimate ACKs). The safe tradeoff is that an
     unknown fraction of injected QACKs are themselves silently ignored by the
     sender (treated as stale by PAWS) — this is a soft failure (no effect that
     round) rather than a connection-breaking one, but it does mean the QACK
     mechanism's effective strength is weaker/noisier than a fully faithful
     implementation would be. See `docs/RESULTS.md` section 1 for how this
     likely affected the dynamic-vs-static comparison.
   - All of this is a **documented deviation**, not a claim of exact
     reproduction — see `docs/RESULTS.md` for the actual measured numbers and
     an honest discussion of where they qualitatively match the paper (baseline
     unfairness direction; static method's over-throttling failure mode) and
     where they don't (the paper's claimed dynamic-beats-static improvement was
     not observed at this compressed timescale/fidelity).

10. **Recurring sawtooth pattern present in ALL THREE scenarios, including the
    no-QACK baseline.** Visual review of `outputs/{no_qack,qack_static,qack_dynamic}_throughput.png`
    side by side shows the same throughput-cycling-to-near-0 sawtooth for roughly
    the first 85-90 seconds of every run, baseline included — so it is not a QACK
    effect, almost certainly an artifact of the single-FIFO `tc tbf` bottleneck
    emulation causing periodic queue starvation across all three flows. Practical
    consequence: the static method's visible effect only appears in the last
    ~25s of its 120s run (~35s after QACK was actually enabled at t=60s), leaving
    the dynamic method effectively no visible window at all — the leading
    candidate explanation for the dynamic-vs-static discrepancy in
    `docs/RESULTS.md` section 1. Full detail in `docs/RESULTS.md`'s "Additional
    honest observation."

11. **Final artifact verification (2026-08-01, before packaging the recording
    guide).** Ran `scripts/verify_outputs.py` (read-only — does not regenerate or
    rerun anything) over every output artifact from the three experiments: all 9
    raw iperf3 JSON logs parse and contain 120 intervals each; all 3 summary
    JSONs parse; all 3 timeseries CSVs have exactly 120 data rows; all 4 PNG
    charts have valid PNG signatures and reasonable file sizes; both QACK proxy
    logs show 35 fired QACKs each. All checks passed — see
    `docs/COMMAND_HISTORY.md` for the exact command and full output.

---
*Add a new dated entry below each time a deviation, workaround, or limitation is
discovered during Phase 4–7 work. Do not delete earlier entries — history matters for
reproducibility.*
