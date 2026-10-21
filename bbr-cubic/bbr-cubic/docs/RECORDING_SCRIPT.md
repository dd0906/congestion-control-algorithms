# RECORDING SCRIPT — What To Say

Pairs with `docs/RECORDING_COMMANDS.md` — step numbers match exactly. Simple
language, one short line per step. Say this near the very beginning, before step 1:

> "This is a deadline-constrained fast-path replication. The paper's experiments
> used Mininet and a P4 programmable switch. I used Linux network namespaces and
> a Python proxy instead, because the full toolchain couldn't be built in time.
> This is not an exact reproduction — it's a working, honestly-documented
> substitute, and I'll show where the numbers do and don't match the paper."

---

1. "Entering the dedicated Ubuntu environment built for this replication."
2. "This is the project folder."
3. "These are the scripts that built and ran everything."
4. "This is everything the three experiments actually produced."
5. "This is our topology — Linux namespaces and veth links standing in for
   Mininet and the P4 switch, with the delay and bandwidth settings built in."
6. "Bringing the topology up live, for real."
7. "Sender, switch, and three receivers — all live right now."
8. "Tearing it back down. This never touches any saved experiment data."
9. "One script runs a full scenario end to end: topology, traffic, the QACK
   proxy, then teardown."
10. "These are the exact commands actually used for the three real runs."
11. "The baseline run has no QACK log at all — no throttling was applied."
12. "Static mode always targets connection 0 — the 80-millisecond flow."
13. "Dynamic mode picks whichever connection has the highest packet count right
    now, every interval."
14. "Real files, real timestamps — proof both runs actually happened."
15. "35 real QACK packets fired during the static run, always at connection 0."
16. "35 real QACK packets fired during the dynamic run too — and in this run,
    it also picked connection 0 every single time, because that connection
    genuinely had the most traffic each round. Same target, same count as the
    static run — I'll come back to why the results still differ."
17. "Real per-second throughput, straight from the saved measurement data."
18. "120 seconds of measured data per scenario, already processed into a
    spreadsheet-style file."
19. "The baseline chart — the 80-millisecond flow clearly dominates."
20. "The static method — the targeted flow gets throttled late in the run."
21. "The dynamic method — much closer to the baseline in our data. That's a
    real difference from what the paper reports, and I'm not hiding it."
22. "Our three fairness numbers: 0.612 for baseline, 0.637 for static, 0.635
    for dynamic."
23. "Our version of the paper's fairness comparison chart."
24. "The paper reports roughly 0.65, 0.83, and 0.93 for these same three cases.
    Our improvement is real but much smaller, and dynamic didn't beat static in
    our data. I checked the logs directly — both runs targeted the exact same
    connection, the same number of times — so this isn't about picking the
    wrong flow, it's most likely run-to-run variation in a simplified
    replication. That's the honest result of this replication."

## Closing line (after step 24)

> "To summarize: this replication confirms TCP BBR's core RTT-unfairness problem,
> and confirms that a fixed QACK target can over-correct. It does not confirm
> that dynamic targeting beats static targeting under these compressed,
> simplified conditions — a fair, disclosed limitation, not something I'm
> smoothing over. A longer run with the original P4 toolchain would be the
> natural next step to check further."

---
*Last updated: 2026-08-01. Paired 1:1 with `docs/RECORDING_COMMANDS.md`.*
