#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import dpkt
import struct

# ------------------------------------------------------------
# 1. PCAP → UDP payloads
# ------------------------------------------------------------
def iter_udp_payloads(path):
    """Yield raw UDP payloads from a PCAP file."""
    with open(path, "rb") as f:
        pcap = dpkt.pcap.Reader(f)
        for ts, buf in pcap:
            try:
                eth = dpkt.ethernet.Ethernet(buf)
                ip = eth.data
                if not isinstance(ip, dpkt.ip.IP):
                    continue
                if ip.p != dpkt.ip.IP_PROTO_UDP:
                    continue
                udp = ip.data
                if udp.data:
                    yield udp.data
            except Exception:
                continue


# ------------------------------------------------------------
# 2. MoldUDP64 parsing
# ------------------------------------------------------------
def parse_moldudp64_packet(payload):
    """
    Parse a MoldUDP64 packet and return raw message blobs.
    Each blob = [MessageType:1][Body:N]
    Zero-length messages are skipped.
    """
    if len(payload) < 10:
        return []

    msg_count = struct.unpack_from(">H", payload, 0)[0]
    seq_num   = struct.unpack_from(">Q", payload, 2)[0]

    messages = []
    offset = 10

    for _ in range(msg_count):
        if offset + 2 > len(payload):
            break

        mlen = struct.unpack_from(">H", payload, offset)[0]
        offset += 2

        # ---- FIX 1: Skip zero-length messages ----
        if mlen == 0:
            continue

        if offset + mlen > len(payload):
            break

        msg_data = payload[offset:offset + mlen]
        offset += mlen

        # ---- FIX 2: Skip empty blobs just in case ----
        if len(msg_data) == 0:
            continue

        messages.append(msg_data)

    return messages


# ------------------------------------------------------------
# 3. ITCH 5.0 message-length table
# ------------------------------------------------------------
ITCH_MSG_LENGTHS = {
    b'S': 11, b'R': 38, b'H': 24, b'Y': 19, b'L': 25,
    b'V': 34, b'W': 11, b'K': 27, b'J': 26, b'h': 20,
    b'A': 35, b'F': 39, b'E': 30, b'C': 34, b'X': 22,
    b'D': 18, b'U': 33, b'P': 43, b'Q': 39, b'B': 18,
    b'I': 49, b'N': 19,
}


# ------------------------------------------------------------
# 4. ITCH message decoding
# ------------------------------------------------------------
def decode_itch_message(msg_data):
    """
    Validate & split ITCH message as (type, body).
    msg_data includes the message type as 1st byte.
    """
    if len(msg_data) == 0:
        return None  # skip empty

    mtype = msg_data[:1]

    # Skip unknown or filler packets
    if mtype not in ITCH_MSG_LENGTHS:
        return None

    expected_len = 1 + ITCH_MSG_LENGTHS[mtype]
    if len(msg_data) != expected_len:
        return None  # do not raise, just skip malformed

    body = msg_data[1:]
    return mtype, body


# ------------------------------------------------------------
# 5. Full pipeline: PCAP → MoldUDP64 → ITCH messages
# ------------------------------------------------------------
def parse_pcap_to_itch(path):
    for udp_payload in iter_udp_payloads(path):
        for raw_msg in parse_moldudp64_packet(udp_payload):
            decoded = decode_itch_message(raw_msg)
            if decoded is not None:
                yield decoded


# In[ ]:


for mtype, body in parse_pcap_to_itch("ny4-xnas-tvitch-a-20250201T010000.pcap"):
    print(mtype)

