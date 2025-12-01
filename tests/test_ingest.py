import io
import struct

from mpid_latency.ingest import iter_itch_messages_from_pcap
from mpid_latency.messages import SystemEvent
from mpid_latency.parser import ITCHReader


def _build_mold_payload(messages):
    session = b"DEMOSESN01"
    sequence = (1).to_bytes(8, "big")
    count = len(messages).to_bytes(2, "big")
    body = b"".join(len(msg).to_bytes(2, "big") + msg for msg in messages)
    return session + sequence + count + body


def _build_ipv4_udp_frame(payload, *, with_vlan=False):
    dest_mac = b"\xaa\xbb\xcc\xdd\xee\xff"
    src_mac = b"\x11\x22\x33\x44\x55\x66"

    eth_type = 0x8100 if with_vlan else 0x0800
    eth_header = dest_mac + src_mac + eth_type.to_bytes(2, "big")

    if with_vlan:
        vlan_tag = b"\x00\x01\x08\x00"  # VLAN 1 then IPv4
    else:
        vlan_tag = b""

    version_ihl = (4 << 4) | 5
    total_length = 20 + 8 + len(payload)
    identification = 0
    flags_fragment = 0
    ttl = 64
    protocol = 17  # UDP
    checksum = 0
    src_ip = b"\x0a\x00\x00\x01"
    dest_ip = b"\x0a\x00\x00\x02"

    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        0,
        total_length,
        identification,
        flags_fragment,
        ttl,
        protocol,
        checksum,
        src_ip,
        dest_ip,
    )

    src_port = 1234
    dest_port = 5678
    udp_length = 8 + len(payload)
    udp_checksum = 0
    udp_header = struct.pack("!HHHH", src_port, dest_port, udp_length, udp_checksum)

    return eth_header + vlan_tag + ip_header + udp_header + payload


def _build_pcap(*frames):
    global_header = struct.pack(">IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    packets = []
    for frame in frames:
        incl_len = len(frame)
        packet_header = struct.pack(">IIII", 0, 0, incl_len, incl_len)
        packets.append(packet_header + frame)
    return global_header + b"".join(packets)


def test_iter_itch_messages_from_pcap_round_trip():
    system_event = b"S" + struct.pack(">HH6sc", 1, 2, (123).to_bytes(6, "big"), b"O")
    mold_payload = _build_mold_payload([system_event])
    frame = _build_ipv4_udp_frame(mold_payload)
    pcap_bytes = _build_pcap(frame)

    messages = list(iter_itch_messages_from_pcap(io.BytesIO(pcap_bytes)))
    assert len(messages) == 1

    reader = ITCHReader(io.BytesIO(messages[0]))
    parsed = list(reader)
    assert isinstance(parsed[0], SystemEvent)
    assert parsed[0].event == "O"


def test_iter_itch_messages_skips_truncated_payload():
    system_event_o = b"S" + struct.pack(">HH6sc", 3, 4, (456).to_bytes(6, "big"), b"O")
    system_event_c = b"S" + struct.pack(">HH6sc", 5, 6, (789).to_bytes(6, "big"), b"C")
    ok_payload = _build_mold_payload([system_event_o])

    two_messages = _build_mold_payload([system_event_c, system_event_c])
    truncated = two_messages[:-4]  # remove part of the trailing message body

    frame1 = _build_ipv4_udp_frame(ok_payload, with_vlan=True)
    frame2 = _build_ipv4_udp_frame(truncated, with_vlan=True)
    pcap_bytes = _build_pcap(frame1, frame2)

    messages = list(iter_itch_messages_from_pcap(io.BytesIO(pcap_bytes)))
    assert len(messages) == 2

    decoded = list(ITCHReader(io.BytesIO(b"".join(messages))))
    assert [msg.event for msg in decoded] == ["O", "C"]