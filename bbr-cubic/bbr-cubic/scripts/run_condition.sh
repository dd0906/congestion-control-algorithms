#!/usr/bin/env bash
# Runs one full BBR-vs-CUBIC condition end-to-end in a single continuous
# process (topology up -> iperf3 server(s) -> client(s) -> live ss -ti
# congestion-control verification -> wait -> teardown). Must stay one
# continuous script — the QACK replication (../scripts/) already discovered
# that separate `wsl -d ...` invocations don't reliably share netns state.
#
# Usage:
#   run_condition.sh <label> <rate_mbit> <delay_ms> <mode> <duration_s> <outdir>
#   mode: solo_bbr | solo_cubic | coexist
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

LABEL="$1"; RATE="$2"; DELAY="$3"; MODE="$4"; DURATION="$5"; OUTDIR="$6"
mkdir -p "$OUTDIR"

echo "[run_condition] $LABEL rate=${RATE}mbit delay=${DELAY}ms mode=$MODE duration=${DURATION}s"
bash "${SCRIPT_DIR}/topo.sh" up "$RATE" "$DELAY"

# receiver-side servers (separate ports so both flows can be told apart)
ip netns exec receiver iperf3 -s -p 6201 > "${OUTDIR}/${LABEL}_bbr_server.log" 2>&1 &
SRV_BBR=$!
ip netns exec receiver iperf3 -s -p 6202 > "${OUTDIR}/${LABEL}_cubic_server.log" 2>&1 &
SRV_CUBIC=$!
sleep 1

PIDS=()
if [ "$MODE" = "solo_bbr" ] || [ "$MODE" = "coexist" ]; then
    ip netns exec senderA iperf3 -c 10.2.2.2 -p 6201 -C bbr -t "$DURATION" -i 1 -J \
        > "${OUTDIR}/${LABEL}_bbr.json" 2> "${OUTDIR}/${LABEL}_bbr.err" &
    PIDS+=($!)
fi
if [ "$MODE" = "solo_cubic" ] || [ "$MODE" = "coexist" ]; then
    ip netns exec senderB iperf3 -c 10.2.2.2 -p 6202 -C cubic -t "$DURATION" -i 1 -J \
        > "${OUTDIR}/${LABEL}_cubic.json" 2> "${OUTDIR}/${LABEL}_cubic.err" &
    PIDS+=($!)
fi

# Live congestion-control verification: capture actual per-socket cong-ctrl
# state from the kernel (ss -ti) partway through the run, not inferred from
# the iperf3 -C flag alone.
sleep 3
if [ "$MODE" = "solo_bbr" ] || [ "$MODE" = "coexist" ]; then
    ip netns exec senderA ss -ti > "${OUTDIR}/${LABEL}_bbr_ss.log" 2>&1 || true
fi
if [ "$MODE" = "solo_cubic" ] || [ "$MODE" = "coexist" ]; then
    ip netns exec senderB ss -ti > "${OUTDIR}/${LABEL}_cubic_ss.log" 2>&1 || true
fi

echo "[run_condition] waiting for ${#PIDS[@]} client(s)..."
wait "${PIDS[@]}"
echo "[run_condition] clients done."

kill -9 "$SRV_BBR" "$SRV_CUBIC" 2>/dev/null || true
bash "${SCRIPT_DIR}/topo.sh" down
echo "[run_condition] $LABEL complete."
