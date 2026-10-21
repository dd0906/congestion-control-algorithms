#!/usr/bin/env bash
# Runs ONE full scenario (topology up -> servers -> clients -> optional QACK
# proxy -> wait -> teardown) as a single continuous process. This MUST stay
# one script/one process: separate `wsl -d ...` invocations were found not to
# share netns/veth/tc state reliably (the WSL instance appears to reset
# runtime network state between separate invocations) — see
# docs/OBSERVATIONS.md item 9.
#
# Usage: run_scenario.sh <scenario_name> <duration_s> <qack_mode: none|static|dynamic> <enable_at_s> <outdir>

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCENARIO="$1"
DURATION="$2"
QACK_MODE="$3"
ENABLE_AT="$4"
OUTDIR="$5"

mkdir -p "$OUTDIR"

echo "[run_scenario] $SCENARIO duration=${DURATION}s qack_mode=${QACK_MODE} enable_at=${ENABLE_AT}s"

bash "${SCRIPT_DIR}/netns_topo.sh" up

# iPerf3 servers, one per receiver, distinct ports
ip netns exec recv1 iperf3 -s -p 5201 > "${OUTDIR}/${SCENARIO}_recv1_server.log" 2>&1 &
S1=$!
ip netns exec recv2 iperf3 -s -p 5202 > "${OUTDIR}/${SCENARIO}_recv2_server.log" 2>&1 &
S2=$!
ip netns exec recv3 iperf3 -s -p 5203 > "${OUTDIR}/${SCENARIO}_recv3_server.log" 2>&1 &
S3=$!
sleep 1

# iPerf3 clients, all three started together, TCP BBR
ip netns exec sender iperf3 -c 10.0.1.2 -p 5201 -C bbr -t "$DURATION" -i 1 -J \
    > "${OUTDIR}/${SCENARIO}_80ms.json" 2> "${OUTDIR}/${SCENARIO}_80ms.err" &
C1=$!
ip netns exec sender iperf3 -c 10.0.2.2 -p 5202 -C bbr -t "$DURATION" -i 1 -J \
    > "${OUTDIR}/${SCENARIO}_40ms.json" 2> "${OUTDIR}/${SCENARIO}_40ms.err" &
C2=$!
ip netns exec sender iperf3 -c 10.0.3.2 -p 5203 -C bbr -t "$DURATION" -i 1 -J \
    > "${OUTDIR}/${SCENARIO}_20ms.json" 2> "${OUTDIR}/${SCENARIO}_20ms.err" &
C3=$!

QACK_PID=""
if [ "$QACK_MODE" != "none" ]; then
    (
      sleep "$ENABLE_AT"
      ip netns exec switch python3 "${SCRIPT_DIR}/qack_proxy.py" "$QACK_MODE" \
          > "${OUTDIR}/${SCENARIO}_qack.log" 2>&1
    ) &
    QACK_BG=$!
fi

echo "[run_scenario] waiting for iperf3 clients ($C1 $C2 $C3)..."
wait "$C1" "$C2" "$C3"
echo "[run_scenario] clients done."

if [ "$QACK_MODE" != "none" ]; then
    pkill -9 -f "qack_proxy.py $QACK_MODE" 2>/dev/null || true
fi
kill -9 "$S1" "$S2" "$S3" 2>/dev/null || true

bash "${SCRIPT_DIR}/netns_topo.sh" down
echo "[run_scenario] $SCENARIO complete."
