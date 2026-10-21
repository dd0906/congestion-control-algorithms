# RESUME HERE — Read This First (Zero-Context Orientation)

You (an AI assistant, or a human) are picking up this project with **no memory of
how it was built**. This file tells you everything you need to know before doing
anything else.

## What this project is

Two related but separate pieces of work, both in this one folder:

1. **The main replication**: paper "RTT Fairness Improvement in TCP BBR with
   Dynamic Target Adjustment" (Kuramo & Yamaguchi, ICCE-Taiwan 2025), at
   `paper/RTT_Fairness_Improvement_in_TCP_BBR_with_Dynamic_Target_Adjustment.pdf`.
2. **An additional, separate experiment** under `bbr_cubic/`: BBR-vs-CUBIC
   coexistence, connecting this project to a different assigned topic. See its
   own section below.

**All experiment work for BOTH is done.** Three real QACK experiments plus four
real BBR-vs-CUBIC experiments were executed, real data was measured and saved,
real charts were generated for both, and full comparisons/writeups exist for
both. **The only remaining work is recording demo videos and presentation** of
the already-completed work — nothing needs to be built, coded, or run again for
either experiment.

**Read `docs/FINAL_STATE.md` next** — it is the complete, self-contained summary
of **both** experiments in one document: sections 1-10 cover the QACK replication
(objective, environment, topology, configuration, all 3 scenarios, results,
deviations from the paper, conclusion); sections 11-18 cover the BBR-vs-CUBIC
experiment (objective, environment, topology, both conditions, results,
limitations, conclusion), clearly marked as a separate addition. Everything you
need to answer questions about either part of this project is in that one file.

## There is also a second, separate experiment: `bbr_cubic/`

After the main QACK replication was completed, a small **additional, isolated**
experiment was added under `bbr_cubic/` to connect this project to a different
assigned topic: "SDN-Based Dynamic Bandwidth Arbitrator for Fair Coexistence of
BBR and CUBIC under Fluctuating Network Conditions." It measures one real BBR flow
and one real CUBIC flow competing simultaneously over the same bottleneck, under
two network conditions. **It is also fully complete** (4 real runs executed,
results measured, 3 required graphs generated, its own README/EXPERIMENT/RESULTS/
RECORDING_GUIDE written). It reuses the same `FairFlow-Ubuntu2204` environment but
its own separate topology/namespaces, and never touched anything in the main
project's `outputs/`, `scripts/`, or `docs/` (verified before and after). Start
with `bbr_cubic/README.md` for the full standalone writeup, or `docs/FINAL_STATE.md`
sections 11-18 for a condensed summary alongside the QACK results — everything
below in this file about the main QACK replication does not apply to `bbr_cubic/`
(it has its own, separate set of guardrails, stated in its own docs).

## What you must NOT do (main QACK replication)

- **Do not rerun `scripts/run_scenario.sh`** for any of the three real scenarios
  (`no_qack`, `qack_static`, `qack_dynamic`). This would overwrite the real,
  already-measured results in `outputs/` with new ones, breaking the numbers
  already written into `docs/RESULTS.md` and `docs/FINAL_STATE.md`.
- **Do not delete or edit any file in `outputs/`.** Every file there is real,
  measured data from an experiment that already happened and cannot be
  regenerated without rerunning the (currently-forbidden) 120-second experiments.
- **Do not modify `docs/RESULTS.md`, `docs/FINAL_STATE.md`, or `docs/EXPERIMENT_LOG.md`**
  unless you are correcting a factual error you have personally re-verified against
  the actual files — these documents describe real measured outcomes, not
  aspirational ones. If something looks off, re-check it against the raw files in
  `outputs/` before touching the docs (see "Known issue already found and fixed"
  below — this happened once already).
- If asked to help record the demo: **use `docs/RECORDING_COMMANDS.md` and
  `docs/RECORDING_SCRIPT.md` exactly as written.** They were tested command-by-
  command against the real files on 2026-08-01. Do not improvise new commands
  without testing them first (read-only) the same way.
- **The same rules apply to `bbr_cubic/`**: do not rerun
  `bbr_cubic/scripts/run_condition.sh` for `solo_bbr`, `solo_cubic`,
  `conditionA`, or `conditionB` (would overwrite real measured results in
  `bbr_cubic/outputs/`), and do not edit/delete anything in `bbr_cubic/outputs/`
  or `bbr_cubic/graphs/`. Use `bbr_cubic/RECORDING_GUIDE.md` for that
  sub-experiment's demo, not the main project's recording files.

## What you CAN safely do

- Anything read-only: `cat`, `grep`, `tail`, `ls`, opening PNGs, running
  `scripts/verify_outputs.py` (it never modifies anything), running
  `scripts/check_summary.py` (read-only).
- `bash scripts/netns_topo.sh up` followed by `bash scripts/netns_topo.sh down` —
  this only creates/destroys Linux network namespaces, never touches `outputs/`.
  Safe to demonstrate live.
- Helping actually record the video, following `docs/RECORDING_COMMANDS.md` +
  `docs/RECORDING_SCRIPT.md`.
- Starting a **new, additional** higher-fidelity re-run using the original
  P4/BMv2/Mininet toolchain (see "Optional follow-up" below) — as long as you save
  results under **new filenames**, not overwriting the existing `no_qack_*`,
  `qack_static_*`, `qack_dynamic_*` files.
- In `bbr_cubic/`: `bash bbr_cubic/scripts/topo.sh up 10 20` followed by
  `bash bbr_cubic/scripts/topo.sh down` — only creates/destroys network
  namespaces, never touches `bbr_cubic/outputs/`. Safe to demonstrate live.
  Anything read-only there (`cat`, `grep`, opening the PNGs in `bbr_cubic/graphs/`)
  is also safe.

## Environment reminder

Everything runs inside a dedicated WSL2 distro named **`FairFlow-Ubuntu2204`**
(Ubuntu 22.04.5 LTS, runs as root, no sudo needed). Enter it with:
```
wsl -d FairFlow-Ubuntu2204
```
Then `cd /mnt/c/Users/PRAVEENA/OneDrive/Desktop/FairFlow_Replication` — that's the
project, visible from Windows at
`C:\Users\PRAVEENA\OneDrive\Desktop\FairFlow_Replication`.

There is a **separate, original** WSL distro also called `Ubuntu` (26.04) — that
one was NOT used for the actual experiments (it was the first environment tried,
found too new for the P4 toolchain installer, and abandoned in favor of the
dedicated distro above). Don't confuse the two.

## Known issue already found and fixed (so you don't "rediscover" it wrong)

An earlier draft of the recording narration incorrectly said the dynamic QACK
method "switches targets between connections." **This was checked against the
full `outputs/qack_dynamic_qack.log` and found to be wrong** — in the actual
executed run, the dynamic method's argmax logic picked the *same* connection
(connection 0, the 80ms flow) in all 35 of 35 fired QACKs, identical to the
static method's fixed target. This is now correctly described everywhere in
`docs/RESULTS.md`, `docs/EXPERIMENT_LOG.md`, `docs/FINAL_STATE.md`, and
`docs/RECORDING_SCRIPT.md`. If you see this claim stated differently anywhere
else, that other place is the one that's wrong — trust the log file
(`outputs/qack_dynamic_qack.log`) over any prose summary, always.

## The one honest, disclosed limitation of this replication

The paper claims the dynamic QACK method improves fairness *more* than the
static method. **Our measured data does not show that** — static (0.637) and
dynamic (0.635) came out almost identical, both far below the paper's claimed
values (~0.83 / ~0.93). This is reported plainly in `docs/RESULTS.md` and
`docs/FINAL_STATE.md`, with the most likely causes explained (fast-path
environment substitution under a 1-hour deadline, scaled-down run duration,
simplified QACK packet-crafting, and probable run-to-run variance since both
runs happened to target the identical connection the identical number of times
yet produced different outcomes). Do not soften or remove this finding — it is
the honest result of this specific replication.

## Optional follow-up (not required, no deadline)

A from-source build of the original P4/BMv2/Mininet toolchain (Mininet + BMv2 +
p4c + P4Runtime) was started but not finished, because it could not complete
within a 1-hour project deadline. A partially-built tree exists at
`FairFlow-Ubuntu2204:/root/p4-tools`, and the intended P4 program is already
written at `scripts/qack.p4` (never compiled). If someone wants a higher-fidelity
re-run later, at the paper's actual 600-second/300-second-enable durations, that
build can be resumed — see `docs/NEXT_TASK.md` and `docs/OBSERVATIONS.md` items
8-9 for exactly where it left off and what was already fixed (two Ubuntu
package-name issues). This is entirely optional and not needed to consider the
current replication complete.

## Quick map of what to read for what

| You want to... | Read |
|---|---|
| Understand BOTH experiments in one document | `docs/FINAL_STATE.md` (sections 1-10 QACK, sections 11-18 BBR-vs-CUBIC) |
| Understand just the QACK experiment | `docs/FINAL_STATE.md` sections 1-10 |
| Record the QACK demo | `docs/RECORDING_COMMANDS.md` + `docs/RECORDING_SCRIPT.md` |
| Find what a specific file is (whole project, both experiments) | `docs/FILE_INDEX.md` |
| See exact QACK numbers vs. the paper | `docs/RESULTS.md` |
| See why something was done a certain way (QACK) | `docs/OBSERVATIONS.md` |
| Check overall status (QACK project; does not yet mention `bbr_cubic/`) | `docs/PROGRESS.md` |
| Understand just the BBR-vs-CUBIC experiment | `bbr_cubic/README.md` -> `bbr_cubic/EXPERIMENT.md`, or `docs/FINAL_STATE.md` sections 11-18 |
| See BBR-vs-CUBIC measured results | `bbr_cubic/RESULTS.md`, or `docs/FINAL_STATE.md` section 16 |
| Record the BBR-vs-CUBIC demo | `bbr_cubic/RECORDING_GUIDE.md` |

---
*Written 2026-08-01, at the very end of the project's active work, specifically so
a future session with zero context (another AI, or the user after closing this
one) can pick this up correctly.*
