# Next Task

**All 7 phases have real deliverables as of 2026-08-01, completed under a 1-hour
deadline via a documented fast-path environment substitution.** See
`docs/PROGRESS.md` for the full breakdown and `docs/RESULTS.md` for the actual
measured comparison against the paper.

## Optional follow-up (not time-boxed, not required)

1. **Record the actual demo video** following the concrete steps already written
   in `docs/RECORDING_GUIDE.md`. Nothing further needs to be built for this —
   it's a straightforward screen-recording pass over already-working commands.

2. **Higher-fidelity re-run** using the original P4/BMv2/Mininet toolchain, which
   was started but not finished in time (build was mid-gRPC in
   `FairFlow-Ubuntu2204:/root/p4-tools` when it was stopped; `scripts/qack.p4` and
   the controller architecture in `docs/PROJECT_PLAN.md` section 7b are ready to
   build on). This would let all 3 experiments run at the paper's actual 600s
   duration (QACK enabled at 300s) instead of our scaled 120s/60s, which
   `docs/RESULTS.md` section 1 flags as the most likely reason our dynamic method
   didn't show the paper's claimed improvement over the static method.

3. If pursuing (2), resume by:
   ```
   wsl -d FairFlow-Ubuntu2204 -- bash -c "cd /root && bash install-p4-dev.sh > install.log 2>&1"
   ```
   (already patched for Ubuntu 22.04.5 package-name drift — see
   `docs/OBSERVATIONS.md` items 8-9 — should run to completion this time if given
   enough wall-clock time, likely another 30-60+ minutes).

Neither of these is required to consider the replication complete for the stated
deadline — they're natural next steps if more time becomes available.

---
*Last updated: 2026-08-01.*
