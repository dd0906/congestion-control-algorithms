# Command History

Every shell/setup command executed during this replication is logged here in
chronological order, so the project can be reproduced or resumed exactly.

Format per entry:
```
### [YYYY-MM-DD HH:MM] <short description>
Phase: <phase number/name>
Command:
    <exact command>
Result: <brief outcome / exit status / notes>
```

---

### [2026-08-01] Project scaffold creation
Phase: 1–3 (documentation scaffold)
Command:
    mkdir -p docs scripts outputs screenshots recordings
Result: Created project directory structure (docs/, scripts/, outputs/, screenshots/,
recordings/) alongside the existing paper/ folder. No environment commands run yet —
Phase 4 (environment setup) has not started.

---

### [2026-08-01] WSL2 Ubuntu environment discovery
Phase: 4 (environment preparation)
Command:
    wsl -l -v ; wsl --version
    wsl -d Ubuntu -- bash -c "cat /etc/os-release; uname -r; sysctl net.ipv4.tcp_available_congestion_control; which python3 pip3 git make gcc cmake; which mn; which simple_switch simple_switch_grpc; which p4c; iperf3 --version"
Result: WSL2 (2.7.8.0) with Ubuntu 26.04 LTS already installed, kernel
6.18.33.1-microsoft-standard-WSL2. `tcp_available_congestion_control` initially only
listed `reno cubic` (no bbr loaded yet), but `/lib/modules/$(uname -r)/kernel/net/ipv4/tcp_bbr.ko`
exists, confirming BBR is available as a loadable module. None of Mininet, BMv2,
p4c, or iPerf3 were installed yet; only python3 and git were present.

### [2026-08-01] Minimal-scope passwordless sudo setup
Phase: 4 (environment preparation)
Command:
    (user-run, one-time) MSYS_NO_PATHCONV=1 wsl -d Ubuntu -- bash "scripts/setup_sudoers.sh"
Result: First attempt used wildcards (`net.ipv4.tcp_*`, `scripts/*`) inside Cmnd_Alias
entries; this WSL's sudo build rejects wildcard argument matching outright
("wildcards are not allowed in command arguments") — visudo -c correctly refused to
install anything, so no broken sudoers state was ever written. Rewrote
`scripts/setup_sudoers.sh` to use only fully literal commands: (1) `modprobe tcp_bbr`
exactly, and (2) `python3` on four fixed, argument-less entrypoint script paths
(`run_smoketest.py`, `run_baseline.py`, `run_qack_static.py`, `run_qack_dynamic.py`).
Dropped `apt-get`/`ip`/`tc`/`sysctl` from the sudoers scope entirely — reasoned that
Mininet's internal `ip`/`tc` calls run as subprocess calls from the already-root
top-level script (no separate sudo needed), and that BBR selection per-socket needs
no sysctl write once the module is loaded, and apt-get is a one-time bulk step better
done interactively than pre-authorized. Draft validated with `visudo -c -f` (dry run
via `--check-only` added to the script) before installing; installed to
`/etc/sudoers.d/fairflow-minimal` (root:root, 0440); full sudoers DB re-validated with
`sudo visudo -c` afterward. Confirmed working via `sudo -n`:
  - `sudo -n modprobe tcp_bbr` → exit 0, bbr now appears in
    `tcp_available_congestion_control`.
  - `sudo -n python3 scripts/run_smoketest.py` (exact authorized path, no args) → exit 0.
  - `sudo -n python3 scripts/run_smoketest.py --foo` (same script, WITH an argument) →
    "interactive authentication is required", exit 1 — confirms the match is exact,
    not loose.
  - `sudo -n whoami` (out of scope) → "interactive authentication is required", exit 1.

### [2026-08-01] Provisioned dedicated Ubuntu 22.04 WSL distro
Phase: 4 (environment preparation)
Command:
    Get-PSDrive C   (checked free disk space: 312.7 GB free, script needs ~35GB)
    curl -sSL -o C:\WSL\FairFlow-Ubuntu2204\rootfs.tar.gz \
      https://cloud-images.ubuntu.com/wsl/jammy/current/ubuntu-jammy-wsl-amd64-ubuntu22.04lts.rootfs.tar.gz
      (resumed once with -C - after a timeout; final size 341,130,963 bytes, matches source)
    wsl --import FairFlow-Ubuntu2204 C:\WSL\FairFlow-Ubuntu2204 C:\WSL\FairFlow-Ubuntu2204\rootfs.tar.gz --version 2
Result: New WSL2 distro "FairFlow-Ubuntu2204" created (Ubuntu 22.04.5 LTS, kernel
6.18.33.1-microsoft-standard-WSL2), default user root, no OOBE prompt encountered.
Verified via `wsl -d FairFlow-Ubuntu2204 -- whoami` -> root. Original default
"Ubuntu" (26.04) distro untouched. See docs/OBSERVATIONS.md item 7 for rationale
(the p4-utils installer only supports/tests Ubuntu 20.04/22.04).

### [2026-08-01] First install-p4-dev.sh run — failed, diagnosed, patched
Phase: 4 (environment preparation)
Command:
    wsl -d FairFlow-Ubuntu2204 -- bash -c "cd /root && bash install-p4-dev.sh > /root/install.log 2>&1"
Result: FAILED (exit 100) during the initial `do_global_setup` apt-get install:
`libgc1c2` has no installation candidate (renamed to `libgc1` upstream) and
`linux-headers-$(uname -r)` doesn't exist for the WSL2 kernel. See
docs/OBSERVATIONS.md item 8. Diagnosed via `tail`/`grep` on /root/install.log and
by extracting every `apt-get install` block from the script
(lines 106, 366, 424, 471, 617, 680) and running `apt-get install -s` (simulate)
against each package list to find all issues in one pass rather than iterating.
Wrote scripts/patch_install_script.py (plain Python string-replace, run via the
already-proven `/mnt/c/...` path — avoided further inline `sed`/quoting through
the Bash-tool -> wsl.exe -> bash -c chain, which had already mangled two prior
sed attempts due to nested escaping) to fix:
  - `libgc1c2` -> `libgc1`
  - removed the `linux-headers-$KERNEL` line (not needed; no kernel modules built)
  - `FRROUTING=true` -> `false`, `DOCUMENTATION=true` -> `false` (neither needed
    for this replication's topology/scope)
Ran:
    wsl -d FairFlow-Ubuntu2204 -- python3 "/mnt/c/.../scripts/patch_install_script.py"
Verified the patched file content directly afterward (sed -n over the relevant
line ranges) before re-running the build.

### [2026-08-01] Re-launched install-p4-dev.sh after patching
Phase: 4 (environment preparation)
Command:
    wsl -d FairFlow-Ubuntu2204 -- bash -c "cd /root && bash install-p4-dev.sh > /root/install.log 2>&1"
    (run_in_background, tracked as a harness background task)
Result: pending — see next entry once it completes or fails again.

### [2026-08-01] Pivot to fast-path environment under 1-hour deadline
Phase: 4/5 (environment + experiments)
Command:
    wsl -d FairFlow-Ubuntu2204 -- bash -c "pkill -9 -f install-p4-dev.sh; pkill -9 -f 'git clone'; pkill -9 -f cc1plus; pkill -9 -f make"
    wsl -d FairFlow-Ubuntu2204 -- bash -c "modprobe tcp_bbr; which iperf3 ip tc; python3 -c 'import scapy'"
    wsl -d FairFlow-Ubuntu2204 -- bash -c "pip3 install --quiet scapy"
Result: Killed the in-progress P4/BMv2 toolchain build (still mid-gRPC after
20+ minutes, not finishable in time). Confirmed `FairFlow-Ubuntu2204` already had
BBR loadable + iperf3 present; installed scapy 2.7.0 via pip (root, instant, no
sudo friction). See docs/OBSERVATIONS.md item 9 for full rationale. Wrote
scripts/netns_topo.sh, scripts/qack_proxy.py, scripts/run_scenario.sh,
scripts/check_summary.py.

### [2026-08-01] Discovered netns state doesn't survive separate wsl invocations
Command:
    wsl -d FairFlow-Ubuntu2204 -- bash "scripts/netns_topo.sh" up   (succeeded)
    wsl -d FairFlow-Ubuntu2204 -- bash -c "ip netns exec sender ping ..."  (FAILED: "Cannot open network namespace 'sender'")
Result: Confirmed separate `wsl -d ...` invocations do not reliably share
netns/veth/tc runtime state (likely WSL2 instance recycling between commands
with no live process). Redesigned scripts/run_scenario.sh to do topology-up,
traffic, QACK proxy, and teardown all within one continuous script/process —
required for correctness, not a style choice.

### [2026-08-01] Smoke test (10s, no QACK)
Command:
    wsl -d FairFlow-Ubuntu2204 -- bash "scripts/run_scenario.sh" smoketest 10 none 0 outputs
Result: Ran end-to-end successfully. Checked via scripts/check_summary.py: 80ms
flow ~9.6 Mbit/s avg vs 40ms/20ms ~2.3-2.6 Mbit/s avg with several 0.0 Mbit/s
intervals (noisy at 10s, but correct unfairness direction). Proceeded to full
120s runs.

### [2026-08-01] Three real experiments executed
Command:
    wsl -d FairFlow-Ubuntu2204 -- bash "scripts/run_scenario.sh" no_qack       120 none    0  outputs
    wsl -d FairFlow-Ubuntu2204 -- bash "scripts/run_scenario.sh" qack_static   120 static  60 outputs
    wsl -d FairFlow-Ubuntu2204 -- bash "scripts/run_scenario.sh" qack_dynamic  120 dynamic 60 outputs
Result: All three completed successfully end-to-end (topology up -> iperf3
servers -> 3 concurrent BBR clients -> QACK proxy at t=60s where applicable ->
wait -> teardown). Full detail and outcomes in docs/EXPERIMENT_LOG.md.

### [2026-08-01] Analysis and Fig. 3/4/5 reproduction
Command:
    wsl -d FairFlow-Ubuntu2204 -- pip3 install --quiet matplotlib
    wsl -d FairFlow-Ubuntu2204 -- python3 scripts/analyze_results.py no_qack ... outputs 60
    wsl -d FairFlow-Ubuntu2204 -- python3 scripts/analyze_results.py qack_static ... outputs 60
    wsl -d FairFlow-Ubuntu2204 -- python3 scripts/analyze_results.py qack_dynamic ... outputs 60
    wsl -d FairFlow-Ubuntu2204 -- python3 scripts/make_fig3.py outputs/no_qack_summary.json outputs/qack_static_summary.json outputs/qack_dynamic_summary.json outputs/fig3_replication.png
Result: Patched analyze_results.py/make_fig3.py to use a parameterized
pre/post-QACK-enable split point (60s for our scaled runs, was hardcoded to
the paper's 300s). Generated outputs/{no_qack,qack_static,qack_dynamic}_{timeseries.csv,throughput.png,summary.json} and outputs/fig3_replication.png. Full
numeric results and comparison against the paper in docs/RESULTS.md.

### [2026-08-01] Final artifact verification before recording package
Phase: 6/7 (results comparison + recording guide finalization)
Command:
    wsl -d FairFlow-Ubuntu2204 -- python3 "/mnt/c/.../scripts/verify_outputs.py"
Result: Read-only check (no experiment rerun, no data regenerated). ALL CHECKS
PASSED: 9 raw iperf3 JSON logs parse cleanly (120 intervals each); 3 summary
JSONs parse; 3 timeseries CSVs have exactly 120 data rows each; 4 PNG charts
(no_qack/qack_static/qack_dynamic throughput + fig3_replication) all have valid
PNG signatures; both QACK proxy logs (`qack_static_qack.log`,
`qack_dynamic_qack.log`) show exactly 35 fired QACKs each. Full per-file output
recorded in the assistant transcript; see docs/OBSERVATIONS.md item 11.

### [2026-08-01] Recording package finalized
Phase: 7 (recording guide)
Command: none (documentation only)
Result: Rewrote docs/RECORDING_GUIDE.md as a concrete 9-segment, ~5-8 minute
sequence (paper -> QACK idea -> our topology -> baseline -> static -> dynamic ->
graphs -> fairness-index comparison -> conclusion), with an exact command, what
to show, narration text, and paper-section correspondence for each segment. Every
command in the sequence is read-only against already-generated artifacts — no
experiment is rerun. Added the sawtooth/tbf-artifact observation (discovered
during chart review) to docs/RESULTS.md and docs/OBSERVATIONS.md item 10.

### [2026-08-01] Final handoff package: verification, correction, and new docs
Phase: 6/7 (final wrap-up for zero-context handoff)
Command:
    wsl -d FairFlow-Ubuntu2204 -- python3 "/mnt/c/.../scripts/verify_outputs.py"
    (re-run, second time — all checks passed again, confirming nothing changed)
    wsl -d FairFlow-Ubuntu2204 -- cat "/mnt/c/.../outputs/qack_dynamic_qack.log"  (full file, not just tail)
    wsl -d FairFlow-Ubuntu2204 -- cat "/mnt/c/.../outputs/qack_static_qack.log"   (full file, not just tail)
Result: Discovered, by reading the FULL dynamic QACK log (not just its tail),
that the dynamic method's argmax logic selected connection 0 in all 35/35 fired
QACKs in this run — identical target and count to the static run — contradicting
an earlier, unverified narration claim that dynamic "switches targets." Corrected
this claim everywhere it appeared: docs/RECORDING_GUIDE.md, and substantially
strengthened the root-cause analysis in docs/RESULTS.md (section 1) and
docs/EXPERIMENT_LOG.md (Run 3) with this verified finding as the new leading
explanation for the dynamic-vs-static discrepancy.

Command:
    MSYS_NO_PATHCONV=1 wsl -d FairFlow-Ubuntu2204 -- bash -c "cd .../outputs && cmd.exe /c start \"\" outputs/no_qack_throughput.png"
    (PowerShell) Get-Process | Where-Object {$_.StartTime -gt (Get-Date).AddSeconds(-30)}
Result: Verified the corrected graph-opening command actually opens the target
PNG file directly (not the containing folder, which `explorer.exe <file>` had
done in an earlier session) — confirmed via Get-Process showing Photos.exe launch
with MainWindowTitle "no_qack_throughput.png". This exact command
(`cmd.exe /c start "" <path>`, forward slashes, run from within the project
directory) is now the one used in docs/RECORDING_COMMANDS.md.

Command:
    (file existence check, 21 distinct paths referenced in RECORDING_COMMANDS.md)
Result: All 21 EXISTS, none MISSING.

Result (overall): Wrote docs/FINAL_STATE.md (complete self-contained experiment
writeup), docs/RECORDING_COMMANDS.md (final tested command sequence, replaces
docs/RECORDING_GUIDE.md for actual recording use), docs/RECORDING_SCRIPT.md
(narration paired 1:1 with RECORDING_COMMANDS.md), docs/FILE_INDEX.md (explains
every file/folder), docs/RESUME_HERE.md (zero-context AI/human handoff entry
point). Updated docs/PROGRESS.md to ~97% (only the actual video recording
remains). No experiment was rerun; no result file in outputs/ was modified or
deleted at any point in this session.

---
*All subsequent Linux-side commands run inside the `FairFlow-Ubuntu2204` distro.*
