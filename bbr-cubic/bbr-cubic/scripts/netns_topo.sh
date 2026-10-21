#!/usr/bin/env bash
# Fast-path topology replacement for the Mininet/BMv2 setup described in the
# paper's Fig. 2 — built with plain Linux network namespaces + veth + tc
# (netem for RTT, tbf for the bottleneck), since a full P4/BMv2 toolchain
# build could not complete within the project's time budget. See
# docs/OBSERVATIONS.md item 9 for the full rationale; this is a documented
# deviation, not a claim of exact toolchain match.
#
# Topology:
#   sender --(RTT 0.0664ms, bottleneck 15mbit)-- switch --(RTT 80ms)-- recv1
#                                                        --(RTT 40ms)-- recv2
#                                                        --(RTT 20ms)-- recv3
#
# Usage: ./netns_topo.sh up | down

set -euo pipefail
ACTION="${1:-up}"

NS_ALL="sender switch recv1 recv2 recv3"

down() {
    for ns in $NS_ALL; do
        ip netns del "$ns" 2>/dev/null || true
    done
}

up() {
    down
    for ns in $NS_ALL; do
        ip netns add "$ns"
    done

    # veth pairs: switch <-> sender, switch <-> recv1/2/3
    ip link add sw-se type veth peer name se-sw
    ip link add sw-r1 type veth peer name r1-sw
    ip link add sw-r2 type veth peer name r2-sw
    ip link add sw-r3 type veth peer name r3-sw

    ip link set se-sw netns sender
    ip link set sw-se netns switch
    ip link set r1-sw netns recv1
    ip link set sw-r1 netns switch
    ip link set r2-sw netns recv2
    ip link set sw-r2 netns switch
    ip link set r3-sw netns recv3
    ip link set sw-r3 netns switch

    # Addressing
    ip netns exec sender   ip addr add 10.0.0.2/24 dev se-sw
    ip netns exec switch   ip addr add 10.0.0.1/24 dev sw-se
    ip netns exec recv1    ip addr add 10.0.1.2/24 dev r1-sw
    ip netns exec switch   ip addr add 10.0.1.1/24 dev sw-r1
    ip netns exec recv2    ip addr add 10.0.2.2/24 dev r2-sw
    ip netns exec switch   ip addr add 10.0.2.1/24 dev sw-r2
    ip netns exec recv3    ip addr add 10.0.3.2/24 dev r3-sw
    ip netns exec switch   ip addr add 10.0.3.1/24 dev sw-r3

    for ns in sender switch recv1 recv2 recv3; do
        ip netns exec "$ns" ip link set lo up
    done
    ip netns exec sender ip link set se-sw up
    ip netns exec switch ip link set sw-se up
    ip netns exec recv1  ip link set r1-sw up
    ip netns exec switch ip link set sw-r1 up
    ip netns exec recv2  ip link set r2-sw up
    ip netns exec switch ip link set sw-r2 up
    ip netns exec recv3  ip link set r3-sw up
    ip netns exec switch ip link set sw-r3 up

    # Routing: sender/receivers use the switch as gateway to reach each other
    ip netns exec sender ip route add default via 10.0.0.1
    ip netns exec recv1  ip route add default via 10.0.1.1
    ip netns exec recv2  ip route add default via 10.0.2.1
    ip netns exec recv3  ip route add default via 10.0.3.1
    ip netns exec switch sysctl -q -w net.ipv4.ip_forward=1

    # RTT emulation (netem delay is one-way per interface; round-trip = sum of
    # both ends). Round-trip targets from Fig. 2: 0.0664/80/40/20 ms.
    # netem is installed as the root qdisc (handle 1:); the sender<->switch
    # link additionally gets a child tbf qdisc (handle 10:) under it for the
    # bottleneck-bandwidth emulation.
    ip netns exec sender tc qdisc add dev se-sw root handle 1: netem delay 33us
    ip netns exec switch tc qdisc add dev sw-se root handle 1: netem delay 33us
    ip netns exec recv1  tc qdisc add dev r1-sw root handle 1: netem delay 40ms
    ip netns exec switch tc qdisc add dev sw-r1 root handle 1: netem delay 40ms
    ip netns exec recv2  tc qdisc add dev r2-sw root handle 1: netem delay 20ms
    ip netns exec switch tc qdisc add dev sw-r2 root handle 1: netem delay 20ms
    ip netns exec recv3  tc qdisc add dev r3-sw root handle 1: netem delay 10ms
    ip netns exec switch tc qdisc add dev sw-r3 root handle 1: netem delay 10ms

    # Bottleneck bandwidth on the shared sender<->switch segment (paper does
    # not state a value — see docs/OBSERVATIONS.md item 1). Applied as a
    # child tbf qdisc under the netem parent on both ends of that link.
    ip netns exec sender tc qdisc add dev se-sw parent 1: handle 10: tbf rate 15mbit burst 32kbit latency 400ms
    ip netns exec switch tc qdisc add dev sw-se parent 1: handle 10: tbf rate 15mbit burst 32kbit latency 400ms

    echo "Topology up."
}

case "$ACTION" in
    up) up ;;
    down) down; echo "Topology down." ;;
    *) echo "usage: $0 up|down"; exit 1 ;;
esac
