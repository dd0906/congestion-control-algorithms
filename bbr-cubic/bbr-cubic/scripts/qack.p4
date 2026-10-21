/*
 * qack.p4 — P4_16 / v1model program for the FairFlow replication.
 *
 * Implements, in the switch data plane:
 *   - Basic L2/L3 forwarding for the fixed topology (Sender, Receiver1/2/3).
 *   - Per-connection (5-tuple) forwarded-packet counters for the 3 static
 *     candidate connections (Sender->Receiver1/2/3), matching the paper's
 *     "counts the number of packets forwarded by the switch in each
 *     connection."
 *   - A global counter of forwarded TCP data packets across all candidates.
 *     Every QACK_INTERVAL (1024) packets, a digest is sent to the controller
 *     with a snapshot of the 3 per-connection counters, last-seen TCP
 *     timestamp (TSval), and last-seen cumulative ACK number per connection.
 *     The controller decides the QACK target (static: fixed; dynamic:
 *     argmax) and crafts/injects the actual QACK packet — see
 *     docs/PROJECT_PLAN.md section 7b for the full design rationale, and
 *     docs/OBSERVATIONS.md item 2 for why this is our own reconstruction of
 *     the (unpublished) original QACK packet-crafting mechanism.
 *   - Standard P4Runtime packet-in/packet-out CPU-port plumbing so the
 *     controller can inject the spoofed QACK "from the switch."
 *
 * NOT yet compiled/tested against the real p4c/bmv2 toolchain (still
 * installing as of this writing) — see docs/EXPERIMENT_LOG.md for when this
 * is first compiled and smoke-tested; expect minor fixes at that point.
 *
 * TCP options parsing note: this program recognizes the common Linux data-
 * segment options pattern NOP,NOP,Timestamps (12 bytes, dataOffset==8),
 * which is what a normal Linux sender emits on data segments once a
 * connection is established with timestamps enabled and no SACK blocks
 * pending. Other options layouts (e.g. an active SACK block after loss) are
 * not parsed; ts_valid is left 0 for those packets, so the digest simply
 * reuses the last successfully-observed TSval/ack for that connection.
 */

#include <core.p4>
#include <v1model.p4>

typedef bit<9>  port_t;
typedef bit<48> mac_addr_t;
typedef bit<32> ip4_addr_t;

const port_t CPU_PORT = 510;
const bit<16> TYPE_IPV4 = 0x0800;
const bit<8>  PROTO_TCP = 6;

const bit<32> QACK_INTERVAL = 1024;   // packets, per paper Section IV
const bit<32> NUM_CANDIDATES = 3;     // Sender->Receiver1/2/3, statically known

/*************************************************************************
 ***********************  H E A D E R S  ********************************
 *************************************************************************/

@controller_header("packet_in")
header packet_in_header_t {
    bit<9> ingress_port;
    bit<7> _pad;
}

@controller_header("packet_out")
header packet_out_header_t {
    bit<9> egress_port;
    bit<7> _pad;
}

header ethernet_t {
    mac_addr_t dstAddr;
    mac_addr_t srcAddr;
    bit<16>    etherType;
}

header ipv4_t {
    bit<4>  version;
    bit<4>  ihl;
    bit<8>  diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3>  flags;
    bit<13> fragOffset;
    bit<8>  ttl;
    bit<8>  protocol;
    bit<16> hdrChecksum;
    ip4_addr_t srcAddr;
    ip4_addr_t dstAddr;
}

header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<3>  res;
    bit<9>  flags;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

// One 32-bit option word at a time, used to recognize NOP,NOP,Timestamps.
header tcp_opt_word_t {
    bit<32> word;
}

header tcp_ts_opt_t {
    bit<8>  kind;   // 8 = Timestamps
    bit<8>  len;    // 10
    bit<32> tsval;
    bit<32> tsecr;
}

struct headers {
    packet_out_header_t packet_out;
    packet_in_header_t  packet_in;
    ethernet_t          ethernet;
    ipv4_t              ipv4;
    tcp_t               tcp;
    tcp_opt_word_t      nop_pair;   // first 4 bytes of options (NOP,NOP,kind,len)
    tcp_ts_opt_t        ts_opt;     // remaining 8 bytes (tsval,tsecr) if it matched
}

struct metadata {
    bit<32> conn_index;   // 0/1/2 for Receiver1/2/3, or invalid marker below
    bool    is_candidate;
    bool    ts_valid;
    bit<32> payload_len;
}

const bit<32> INVALID_CONN = 0xFFFFFFFF;

/*************************************************************************
 ***********************  P A R S E R  **********************************
 *************************************************************************/

parser QackParser(packet_in packet,
                   out headers hdr,
                   inout metadata meta,
                   inout standard_metadata_t standard_metadata) {

    state start {
        meta.is_candidate = false;
        meta.ts_valid = false;
        meta.conn_index = INVALID_CONN;
        transition select(standard_metadata.ingress_port) {
            CPU_PORT: parse_packet_out;
            default:  parse_ethernet;
        }
    }

    state parse_packet_out {
        packet.extract(hdr.packet_out);
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default:   accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            PROTO_TCP: parse_tcp;
            default:   accept;
        }
    }

    state parse_tcp {
        packet.extract(hdr.tcp);
        meta.payload_len = (bit<32>) hdr.ipv4.totalLen
                          - (bit<32>) 4 * (bit<32>) hdr.ipv4.ihl
                          - (bit<32>) 4 * (bit<32>) hdr.tcp.dataOffset;
        // Only the common case is parsed: dataOffset == 8 (12 option bytes)
        // with the first word looking like NOP,NOP,kind=8,len=10.
        transition select(hdr.tcp.dataOffset) {
            8w8: parse_tcp_opt_word;
            default: accept;
        }
    }

    state parse_tcp_opt_word {
        packet.extract(hdr.nop_pair);
        // hdr.nop_pair.word bytes are [NOP=1][NOP=1][kind][len]
        transition select(hdr.nop_pair.word) {
            0x0101080A &&& 0xFFFFFFFF: parse_tcp_ts_opt; // kind=8 len=10 (0x0A)
            default: accept;
        }
    }

    state parse_tcp_ts_opt {
        packet.extract(hdr.ts_opt);
        meta.ts_valid = true;
        transition accept;
    }
}

/*************************************************************************
 ************  C H E C K S U M   V E R I F I C A T I O N  ****************
 *************************************************************************/

control QackVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }  // verification skipped; not needed for forwarding correctness here
}

/*************************************************************************
 **************  I N G R E S S   P R O C E S S I N G  ********************
 *************************************************************************/

control QackIngress(inout headers hdr,
                     inout metadata meta,
                     inout standard_metadata_t standard_metadata) {

    // index 0/1/2 <-> Sender->Receiver1/2/3. Populated by the control plane
    // at startup (static candidate set, per paper Section III.B).
    register<bit<32>>(NUM_CANDIDATES) pkt_counter;
    register<bit<32>>(NUM_CANDIDATES) last_tsval;
    register<bit<32>>(NUM_CANDIDATES) last_cum_ack;
    register<bit<32>>(1) global_counter;

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action set_egress_port(port_t port) {
        standard_metadata.egress_spec = port;
    }

    action set_connection_index(bit<32> index) {
        meta.conn_index = index;
        meta.is_candidate = true;
    }

    // Populated by the controller: one exact-match entry per candidate
    // 5-tuple (Sender->Receiver1, ->Receiver2, ->Receiver3).
    table candidate_connections {
        key = {
            hdr.ipv4.srcAddr: exact;
            hdr.ipv4.dstAddr: exact;
            hdr.tcp.srcPort:  exact;
            hdr.tcp.dstPort:  exact;
        }
        actions = { set_connection_index; NoAction; }
        default_action = NoAction();
        size = 8;
    }

    // Populated by the controller: static L3 forwarding for the 4 hosts.
    table ipv4_forward {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = { set_egress_port; drop; }
        default_action = drop();
        size = 16;
    }

    apply {
        if (hdr.packet_out.isValid()) {
            // Controller-injected packet (the QACK itself): just send it out
            // the requested port and strip the packet_out header.
            standard_metadata.egress_spec = hdr.packet_out.egress_port;
            hdr.packet_out.setInvalid();
            return;
        }

        if (hdr.ipv4.isValid()) {
            ipv4_forward.apply();
        }

        if (hdr.tcp.isValid()) {
            candidate_connections.apply();

            if (meta.is_candidate) {
                bit<32> cnt;
                pkt_counter.read(cnt, meta.conn_index);
                cnt = cnt + 1;
                pkt_counter.write(meta.conn_index, cnt);

                if (meta.ts_valid) {
                    last_tsval.write(meta.conn_index, hdr.ts_opt.tsval);
                }
                last_cum_ack.write(meta.conn_index,
                                    hdr.tcp.seqNo + meta.payload_len);

                bit<32> gcnt;
                global_counter.read(gcnt, 0);
                gcnt = gcnt + 1;
                global_counter.write(0, gcnt);

                if (gcnt >= QACK_INTERVAL) {
                    // Snapshot everything the controller needs, then let the
                    // controller reset all counters after it reads this
                    // digest (matches "each counter is reset to 0").
                    bit<32> c0; bit<32> c1; bit<32> c2;
                    bit<32> t0; bit<32> t1; bit<32> t2;
                    bit<32> a0; bit<32> a1; bit<32> a2;
                    pkt_counter.read(c0, 0); pkt_counter.read(c1, 1); pkt_counter.read(c2, 2);
                    last_tsval.read(t0, 0);  last_tsval.read(t1, 1);  last_tsval.read(t2, 2);
                    last_cum_ack.read(a0, 0); last_cum_ack.read(a1, 1); last_cum_ack.read(a2, 2);

                    digest<qack_digest_t>(1, {c0, c1, c2, t0, t1, t2, a0, a1, a2});

                    global_counter.write(0, 0);
                    pkt_counter.write(0, 0); pkt_counter.write(1, 0); pkt_counter.write(2, 0);
                }
            }
        }
    }
}

struct qack_digest_t {
    bit<32> count0;
    bit<32> count1;
    bit<32> count2;
    bit<32> tsval0;
    bit<32> tsval1;
    bit<32> tsval2;
    bit<32> ack0;
    bit<32> ack1;
    bit<32> ack2;
}

/*************************************************************************
 ****************  E G R E S S   P R O C E S S I N G  *********************
 *************************************************************************/

control QackEgress(inout headers hdr,
                    inout metadata meta,
                    inout standard_metadata_t standard_metadata) {
    apply {
        if (standard_metadata.ingress_port == CPU_PORT) {
            // nothing extra needed; egress_spec already set in ingress
        } else if (standard_metadata.egress_port == CPU_PORT) {
            hdr.packet_in.setValid();
            hdr.packet_in.ingress_port = standard_metadata.ingress_port;
        }
    }
}

/*************************************************************************
 *************   C H E C K S U M   C O M P U T A T I O N   ***************
 *************************************************************************/

control QackComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(
            hdr.ipv4.isValid(),
            { hdr.ipv4.version, hdr.ipv4.ihl, hdr.ipv4.diffserv,
              hdr.ipv4.totalLen, hdr.ipv4.identification, hdr.ipv4.flags,
              hdr.ipv4.fragOffset, hdr.ipv4.ttl, hdr.ipv4.protocol,
              hdr.ipv4.srcAddr, hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

/*************************************************************************
 ***********************  D E P A R S E R  ********************************
 *************************************************************************/

control QackDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.packet_in);
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.tcp);
        packet.emit(hdr.nop_pair);
        packet.emit(hdr.ts_opt);
    }
}

/*************************************************************************
 ***********************  S W I T C H  ************************************
 *************************************************************************/

V1Switch(
    QackParser(),
    QackVerifyChecksum(),
    QackIngress(),
    QackEgress(),
    QackComputeChecksum(),
    QackDeparser()
) main;
