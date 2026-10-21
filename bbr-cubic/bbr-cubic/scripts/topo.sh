#!/usr/bin/env bash
# BBR-vs-CUBIC coexistence topology. Reuses the same Linux netns+veth+tc
# approach as ../scripts/netns_topo.sh (the QACK replication), isolated under
# bbr_cubic/ and touching none of that project's namespaces or files.
#
# Topology:
#   senderA (BBR)  --fast link--\
#                                 switch --BOTTLENECK link-- receiver
#   senderB (CUBIC) --fast link--/
#
# Both flows funnel through the single switch-receiver link, which is where
# the shared bottleneck (rate + delay) is applied — same technique as the
# QACK replication's shared sender-switch link.
#
# Usage: topo.sh up <rate_mbit> <delay_ms> | down
set -euo pipefail
ACTION="${1:-up}"
NS_ALL="senderA senderB switch receiver"

down() {
    for ns in $NS_ALL; do ip netns del "$ns" 2>/dev/null || true; done
}

up() {
    RATE_MBIT="$2"
    DELAY_MS="$3"
    down
    for ns in $NS_ALL; do ip netns add "$ns"; done

    ip link add a-sw type veth peer name sw-a
    ip link add b-sw type veth peer name sw-b
    ip link add sw-r type veth peer name r-sw

    ip link set a-sw netns senderA
    ip link set sw-a netns switch
    ip link set b-sw netns senderB
    ip link set sw-b netns switch
    ip link set sw-r netns switch
    ip link set r-sw netns receiver

    ip netns exec senderA ip addr add 10.2.0.2/24 dev a-sw
    ip netns exec switch  ip addr add 10.2.0.1/24 dev sw-a
    ip netns exec senderB ip addr add 10.2.1.2/24 dev b-sw
    ip netns exec switch  ip addr add 10.2.1.1/24 dev sw-b
    ip netns exec switch  ip addr add 10.2.2.1/24 dev sw-r
    ip netns exec receiver ip addr add 10.2.2.2/24 dev r-sw

    for ns in $NS_ALL; do ip netns exec "$ns" ip link set lo up; done
    ip netns exec senderA  ip link set a-sw up
    ip netns exec switch   ip link set sw-a up
    ip netns exec senderB  ip link set b-sw up
    ip netns exec switch   ip link set sw-b up
    ip netns exec switch   ip link set sw-r up
    ip netns exec receiver ip link set r-sw up

    ip netns exec senderA  ip route add default via 10.2.0.1
    ip netns exec senderB  ip route add default via 10.2.1.1
    ip netns exec receiver ip route add default via 10.2.2.1
    ip netns exec switch sysctl -q -w net.ipv4.ip_forward=1

    # Shared bottleneck: split DELAY_MS across both ends of the switch<->receiver
    # link (same round-trip convention as ../scripts/netns_topo.sh), rate-limited
    # to RATE_MBIT on both ends.
    HALF_DELAY="$(echo "$DELAY_MS/2" | bc -l)ms"
    ip netns exec switch   tc qdisc add dev sw-r root handle 1: netem delay "$HALF_DELAY"
    ip netns exec receiver tc qdisc add dev r-sw root handle 1: netem delay "$HALF_DELAY"
    ip netns exec switch   tc qdisc add dev sw-r parent 1: handle 10: tbf rate "${RATE_MBIT}mbit" burst 32kbit latency 400ms
    ip netns exec receiver tc qdisc add dev r-sw parent 1: handle 10: tbf rate "${RATE_MBIT}mbit" burst 32kbit latency 400ms

    echo "Topology up: bottleneck=${RATE_MBIT}mbit delay=${DELAY_MS}ms (round-trip)"
}

case "$ACTION" in
    up) up "$@" ;;
    down) down; echo "Topology down." ;;
    *) echo "usage: $0 up <rate_mbit> <delay_ms> | down"; exit 1 ;;
esac
