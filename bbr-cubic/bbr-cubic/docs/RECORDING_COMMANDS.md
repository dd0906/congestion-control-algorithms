# RECORDING COMMANDS — Final, Tested Sequence

Every command below was tested against the actual project files on 2026-08-01 and
confirmed working. **None of them rerun an experiment, modify any file, or delete
anything.** Pair this file with `docs/RECORDING_SCRIPT.md` (what to say for each
numbered step — the numbers match).

**Do not substitute `explorer.exe <file>`** to open the PNG charts — it was tested
and opens the containing folder instead of the image. Use the `cmd.exe /c start ""
<path>` form below instead; it was tested and confirmed to open the exact file
(verified via `Get-Process` showing `Photos.exe` launching with the correct
`MainWindowTitle`).

One continuous terminal, in this order:

```
1.  wsl -d FairFlow-Ubuntu2204

2.  cd /mnt/c/Users/PRAVEENA/OneDrive/Desktop/FairFlow_Replication

3.  ls scripts/

4.  ls outputs/

5.  cat scripts/netns_topo.sh

6.  bash scripts/netns_topo.sh up

7.  ip netns list

8.  bash scripts/netns_topo.sh down

9.  cat scripts/run_scenario.sh

10. grep -A2 "^Command:" docs/EXPERIMENT_LOG.md

11. ls outputs/no_qack*

12. grep -n "STATIC_TARGET" scripts/qack_proxy.py

13. grep -n "max(counters" scripts/qack_proxy.py

14. ls -la outputs/qack_static_qack.log outputs/qack_dynamic_qack.log

15. tail -5 outputs/qack_static_qack.log

16. tail -5 outputs/qack_dynamic_qack.log

17. python3 scripts/check_summary.py outputs/no_qack_80ms.json outputs/no_qack_40ms.json outputs/no_qack_20ms.json

18. wc -l outputs/no_qack_timeseries.csv outputs/qack_static_timeseries.csv outputs/qack_dynamic_timeseries.csv

19. cmd.exe /c start "" outputs/no_qack_throughput.png

20. cmd.exe /c start "" outputs/qack_static_throughput.png

21. cmd.exe /c start "" outputs/qack_dynamic_throughput.png

22. cat outputs/no_qack_summary.json outputs/qack_static_summary.json outputs/qack_dynamic_summary.json

23. cmd.exe /c start "" outputs/fig3_replication.png

24. cat docs/RESULTS.md
```

## Expected output for each step (verify against this before/while recording)

1. **Prompt changes** to a Linux prompt inside `FairFlow-Ubuntu2204`.
2. **No output** — just returns to a prompt, now in the project folder.
3. Lists: `README.md`, `analyze_results.py`, `check_summary.py`, `make_fig3.py`,
   `netns_topo.sh`, `patch_install_script.py`, `qack.p4`, `qack_proxy.py`,
   `run_scenario.sh`, `run_smoketest.py`, `setup_sudoers.sh`, `verify_outputs.py`.
4. Lists: `README.md`, `fig3_replication.png`, all `no_qack_*`, `qack_static_*`,
   `qack_dynamic_*`, and `smoketest_*` files.
5. Full script text prints — namespace/veth setup, `tc netem`/`tc tbf` lines.
6. Prints `Topology up.`
7. Prints 5 names: `sender`, `switch`, `recv1`, `recv2`, `recv3`.
8. Prints `Topology down.`
9. Full script text prints — topology up, iperf3 servers, iperf3 clients, optional
   QACK proxy, wait, teardown.
10. Three `Command:` blocks, one per scenario (`no_qack`, `qack_static`,
    `qack_dynamic`), each showing the exact `run_scenario.sh ...` invocation used.
11. Lists only `no_qack_*` files (12 files: 3 `.json`, 3 `.err`, 3 server logs, 1
    `.csv`, 1 summary `.json`, 1 `.png`). **No** `no_qack_qack.log` — confirms no
    QACK ran in this scenario.
12. Two lines: the `STATIC_TARGET = 0` definition and the line using it in the
    target-selection ternary.
13. One line: the same ternary line, matched via `max(counters`.
14. Two files listed with real sizes (~2.9 KB each) and real timestamps.
15. 5 lines, each `[qack_proxy] QACK #31` through `#35`, all showing `-> conn0`.
16. 5 lines, each `[qack_proxy] QACK #31` through `#35`, **also** all showing
    `-> conn0` — see `docs/RECORDING_SCRIPT.md` step 16 for why this matters.
17. Three `=== outputs/no_qack_*.json ===` blocks, each with an `avg mbps:` line
    and per-second throughput values.
18. Three line counts, each **121** (120 data rows + 1 header row), plus a total
    line of 363.
19-21, 23. The Windows Photos app opens showing that exact chart image.
22. Three JSON blocks print back to back, showing `avg_fairness_index_overall`
    0.6115... / 0.6344... / 0.6181... and the `_post_split` values 0.6154... /
    0.6366... / 0.6348... for `no_qack` / `qack_static` / `qack_dynamic`
    respectively.
24. The full contents of `docs/RESULTS.md` print, including the Fig. 3 comparison
    table and the honest discussion of what matched/didn't match the paper.

---
*Tested 2026-08-01 against the actual project files. If any step's real output
differs from "Expected output" above, stop and re-check before recording — do not
assume the file changed silently; verify with `scripts/verify_outputs.py` first.*
