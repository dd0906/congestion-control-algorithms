"""
quic_dc_sim.py  --  QUIC-DC Network Simulator
===============================================
Paper: "QUIC Delay Control: an implementation of congestion and delay control"
       Mascolo et al., arXiv:2507.00896

Algorithm (Section 3):
  OWQD = cumulative one-way queueing delay (Eq. 4-5)
  Congestion declared when OWQD > threshold (Eq. 6)
  Reaction: cwnd = BWE x RTT_min (TCP Westwood+)

Network model (Section 4):
  Bottleneck: 25 Mbps, RTT_min = 50 ms, file = 100 MB
  Buffer: 0.5 / 1 / 2 / 4 x BDP  (tail-drop)
  Time step: 1 RTT

Key correctness principle:
  In one RTT of duration dt=RTT_min, the link can deliver at most
  BDP_BYTES = link_rate * RTT_min bytes.
  The sender can have up to cwnd bytes in flight.
  Actual throughput = min(cwnd, in_flight_capacity, link_rate * rtt)
  Packets are dropped only when the buffer is full at the bottleneck.
"""

import csv
import os
import time

# ---------------------------------------------------------------------------
# Network parameters (matching paper Section 4 exactly)
# ---------------------------------------------------------------------------
LINK_BW_MBPS = 25
RTT_MIN_MS   = 50
FILE_MB      = 100
MSS          = 1460

LINK_Bps  = LINK_BW_MBPS * 1e6 / 8     # 3,125,000 B/s
RTT_MIN_S = RTT_MIN_MS / 1000.0
BDP_BYTES = LINK_Bps * RTT_MIN_S        # 156,250 bytes per RTT

FILE_BYTES    = FILE_MB * 1024 * 1024   # 104,857,600 bytes
BDP_MULTS     = [0.5, 1.0, 2.0, 4.0]
DC_THRESHOLDS = [0.10, 0.20, 0.50, 0.80]
MAX_STEPS     = 50000    # safety: 50000 RTTs x 50ms = 2500 seconds max

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "raw_outputs")


def simulate(name, algo, buf_bytes, owqd_frac=None):
    """
    Discrete-time simulation, one step = one RTT.

    Network model:
      - The bottleneck queue starts at 0.
      - Each RTT: sender injects bytes_in_flight = min(cwnd, remaining_file).
      - The link drains BDP_BYTES per RTT regardless of queue.
      - Any bytes injected beyond what the link can drain that RTT go into the queue.
      - If queue + excess > buf_bytes  -->  tail drop, excess packets discarded.
      - Actual delivery = bytes drained from queue + newly injected bytes
                        that fit within the RTT drain budget.
    """
    # State
    cwnd     = 10.0 * MSS
    ssthresh = float("inf")
    bwe      = LINK_Bps
    owqd     = 0.0        # cumulative OWQD (seconds)
    queue    = 0.0        # buffered bytes at bottleneck (in addition to what link carries)
    # Cubic-specific
    wmax, t_epoch = cwnd, 0.0
    C_CUBIC, BETA_CUBIC = 0.4, 0.7
    # BBRv2-specific
    bbr_phase, bbr_cnt = "startup", 0

    buf_time    = buf_bytes / LINK_Bps    # buffer size in seconds
    owqd_thr    = (owqd_frac or 0.0) * buf_time

    # BWE low-pass filter: paper Eq.7 uses alpha=0.7 for QUIC-DC (faster)
    alpha = 0.7 if algo == "quic_dc" else 0.9

    bytes_delivered = 0.0
    total_sent_pkts = 0
    total_lost_pkts = 0
    elapsed_s       = 0.0
    records         = []

    for step in range(MAX_STEPS):
        if bytes_delivered >= FILE_BYTES:
            break

        # -------- How many bytes does the sender push this RTT? --------
        remaining = FILE_BYTES - bytes_delivered
        # Bytes in flight = min(cwnd, remaining file)
        in_flight = min(cwnd, remaining)

        # -------- Bottleneck queue & delivery model --------
        # Link drain budget per RTT = BDP_BYTES
        drain_budget = BDP_BYTES

        # Packets from queue drained first
        from_queue   = min(queue, drain_budget)
        budget_left  = drain_budget - from_queue
        queue        = queue - from_queue

        # New bytes from sender: first fill remaining drain budget, rest go to queue
        new_delivered  = min(in_flight, budget_left)
        new_to_queue   = in_flight - new_delivered

        # Queue overflow check (tail-drop)
        overflow = max(0.0, (queue + new_to_queue) - buf_bytes)
        new_to_queue = max(0.0, new_to_queue - overflow)
        queue        = min(queue + new_to_queue, buf_bytes)

        # Actual bytes delivered this RTT
        delivered_B = from_queue + new_delivered

        # Packet counts (approximate: 1 pkt = 1 MSS)
        pkts_sent  = max(1, int(in_flight / MSS))
        pkts_lost  = int(overflow / MSS)
        pkts_ok    = pkts_sent - pkts_lost

        bytes_delivered += delivered_B
        total_sent_pkts += pkts_sent
        total_lost_pkts += pkts_lost

        # -------- Queueing delay & RTT --------
        q_delay_s = queue / LINK_Bps
        rtt_s     = RTT_MIN_S + q_delay_s

        # -------- BWE update --------
        sample = delivered_B / RTT_MIN_S
        bwe    = alpha * bwe + (1 - alpha) * sample

        # -------- OWQD estimate (Eq. 4-5) --------
        if algo == "quic_dc":
            inter_dep = MSS / LINK_Bps
            # Inter-arrival stretched by queue fill ratio
            fill_ratio = 1.0 + (queue / (buf_bytes + 1.0))
            inter_arr  = inter_dep * fill_ratio
            owqd = max(0.0, owqd + (inter_arr - inter_dep))

        # -------- Congestion events --------
        loss_ev = pkts_lost > 0
        owqd_ev = (algo == "quic_dc") and (owqd > owqd_thr)
        cong    = loss_ev or owqd_ev

        # -------- Window update --------
        if algo == "cubic":
            if loss_ev:
                wmax     = cwnd
                ssthresh = max(cwnd * BETA_CUBIC, 2 * MSS)
                cwnd     = ssthresh
                t_epoch  = elapsed_s
            else:
                t   = elapsed_s - t_epoch
                K   = (wmax * (1 - BETA_CUBIC) / C_CUBIC) ** (1/3)
                w_c = C_CUBIC * (t - K)**3 + wmax
                cwnd = max(w_c, cwnd + MSS / max(cwnd, 1))

        elif algo == "new_reno":
            if loss_ev:
                ssthresh = max(cwnd / 2.0, 2 * MSS)
                cwnd     = ssthresh
            elif cwnd < ssthresh:
                cwnd += MSS
            else:
                cwnd += MSS * MSS / cwnd

        elif algo in ("westwood", "quic_dc"):
            if cong:
                wnd      = bwe * RTT_MIN_S
                ssthresh = max(wnd, 2 * MSS)
                cwnd     = ssthresh
                if algo == "quic_dc":
                    owqd = 0.0
            elif cwnd < ssthresh:
                cwnd += MSS
            else:
                cwnd += MSS * MSS / cwnd

        elif algo == "bbrv2":
            if bbr_phase == "startup":
                cwnd = 2.0 * BDP_BYTES * 1.25
            elif bbr_phase == "drain":
                cwnd = 2.0 * BDP_BYTES * 0.75
            else:
                cwnd = 2.0 * BDP_BYTES
            bbr_cnt += 1
            if bbr_cnt > 8:
                bbr_phase = {"startup": "probe", "probe": "drain",
                             "drain": "probe"}.get(bbr_phase, "probe")
                bbr_cnt = 0

        # Cap cwnd
        cwnd = max(MSS, min(cwnd, 4000 * MSS))

        # -------- Record --------
        tp_mbps   = delivered_B * 8 / RTT_MIN_S / 1e6
        loss_rate = pkts_lost / max(1, pkts_sent)
        owqd_ms   = owqd * 1000 if algo == "quic_dc" else 0.0

        records.append({
            "time_ms"        : round(elapsed_s * 1000, 1),
            "throughput_mbps": round(tp_mbps, 4),
            "rtt_ms"         : round(rtt_s * 1000, 3),
            "cwnd_bytes"     : round(cwnd),
            "loss_rate"      : round(loss_rate, 6),
            "owqd_ms"        : round(owqd_ms, 4),
        })
        elapsed_s += RTT_MIN_S

    # -------- Summary --------
    if not records:
        records = [{"time_ms": 0, "throughput_mbps": 0, "rtt_ms": RTT_MIN_MS,
                    "cwnd_bytes": MSS, "loss_rate": 0, "owqd_ms": 0}]

    rtts   = [r["rtt_ms"] for r in records]
    tps    = [r["throughput_mbps"] for r in records]
    rtts_s = sorted(rtts)
    n      = len(rtts_s)
    dur_s  = elapsed_s
    gp     = bytes_delivered * 8 / max(dur_s, 1e-9) / 1e6
    lp     = 100.0 * total_lost_pkts / max(1, total_sent_pkts)

    return records, {
        "name"               : name,
        "goodput_mbps"       : round(gp, 3),
        "avg_rtt_ms"         : round(sum(rtts) / n, 2),
        "median_rtt_ms"      : round(rtts_s[n // 2], 2),
        "p95_rtt_ms"         : round(rtts_s[int(0.95 * n)], 2),
        "avg_throughput_mbps": round(sum(tps) / max(1, len(tps)), 3),
        "loss_pct"           : round(lp, 4),
        "duration_s"         : round(dur_s, 2),
    }


def run_experiments():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_summaries = []

    print(f"{'Buffer':<12} {'Algorithm':<28} {'Goodput':>9} {'Med-RTT':>10} {'Loss%':>8}")
    print("-" * 72)

    for bdp_mult in BDP_MULTS:
        buf_bytes = bdp_mult * BDP_BYTES
        label     = f"{bdp_mult}BDP"

        experiments = [(f"QUIC-DC ({int(t*100)}%)", "quic_dc", t) for t in DC_THRESHOLDS]
        experiments += [("Cubic","cubic",None),("BBRv2","bbrv2",None),
                        ("NewReno","new_reno",None),("Westwood+","westwood",None)]

        for name, algo, owqd_frac in experiments:
            t0 = time.perf_counter()
            records, summary = simulate(name, algo, buf_bytes, owqd_frac)
            elapsed = time.perf_counter() - t0
            summary["buffer"]   = label
            summary["bdp_mult"] = bdp_mult
            all_summaries.append(summary)

            safe = (name.replace("/","_").replace(" ","_")
                        .replace("(","").replace(")","").replace("%","pct"))
            csv_path = os.path.join(OUTPUT_DIR, f"timeseries_{label}_{safe}.csv")
            with open(csv_path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=records[0].keys())
                w.writeheader()
                w.writerows(records)

            print(f"{label:<12} {name:<28} {summary['goodput_mbps']:>8.2f}M "
                  f"{summary['median_rtt_ms']:>9.1f}ms "
                  f"{summary['loss_pct']:>7.3f}%  ({elapsed*1000:.0f}ms sim)")

        print()

    summary_path = os.path.join(OUTPUT_DIR, "summary_all.csv")
    with open(summary_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_summaries[0].keys()))
        w.writeheader()
        w.writerows(all_summaries)

    print(f"Data written to: {OUTPUT_DIR}")
    return all_summaries


if __name__ == "__main__":
    print("=" * 70)
    print("QUIC-DC Simulation  (arXiv:2507.00896  --  Mascolo et al.)")
    print(f"Link: {LINK_BW_MBPS} Mbps  | RTT_min: {RTT_MIN_MS} ms | File: {FILE_MB} MB")
    print(f"BDP  = {BDP_BYTES/1024:.1f} KB  | Step = {RTT_MIN_MS} ms/RTT")
    print("=" * 70)
    run_experiments()
    print("Done.")
