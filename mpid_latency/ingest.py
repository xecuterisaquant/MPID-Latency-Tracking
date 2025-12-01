"""Helpers for extracting ITCH payloads from MoldUDP64 wrapped ITCH data."""

from __future__ import annotations

import struct
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator


class PcapDecodeError(RuntimeError):
	"""Raised when the pcap stream cannot be decoded."""


class MoldUDPDecodeError(RuntimeError):
	"""Raised when a MoldUDP64 payload is malformed."""


_PCAP_MAGIC_TO_STRUCT_ENDIANNESS = {
	0xA1B2C3D4: ">",
	0xD4C3B2A1: "<",
	0xA1B23C4D: ">",
	0x4D3CB2A1: "<",
}

_ETHERNET_HEADER_LENGTH = 14
_ETHERTYPE_IPV4 = 0x0800
_VLAN_ETHERTYPES = {0x8100, 0x88A8, 0x9100}
_IP_HEADER_MIN_LENGTH = 20
_IP_PROTOCOL_UDP = 17
_UDP_HEADER_LENGTH = 8


def iter_itch_messages_from_pcap(source: str | Path | BinaryIO) -> Iterator[bytes]:
	"""Yield ITCH messages ready for :class:`mpid_latency.parser.ITCHReader`.

	Each yielded chunk contains the ITCH message type, a two-byte big-endian
	length that includes those three bytes, and the message body bytes. Messages
	are extracted from UDP payloads that follow the MoldUDP64 framing format.
	"""

	with _open_binary_stream(source) as fh:
		endianness = _read_pcap_global_header(fh)
		for payload in _iter_udp_payloads(fh, endianness):
			for message in _iter_mold_messages(payload):
				if not message:
					continue
				msg_type = message[:1]
				body = message[1:]
				length_value = len(body) + 3
				yield msg_type + length_value.to_bytes(2, "big") + body


def write_itch_stream_from_pcap(
	source: str | Path | BinaryIO, destination: str | Path
) -> Path:
	"""Write the extracted ITCH byte stream to *destination*.

	Returns the resolved :class:`Path` of the written file to support chaining in
	higher-level ingestion workflows.
	"""

	dest_path = Path(destination).expanduser().resolve()
	dest_path.parent.mkdir(parents=True, exist_ok=True)

	with dest_path.open("wb") as out:
		for message in iter_itch_messages_from_pcap(source):
			out.write(message)

	return dest_path


@contextmanager
def _open_binary_stream(source: str | Path | BinaryIO) -> Iterator[BinaryIO]:
	if isinstance(source, (str, Path)):
		fh = Path(source).expanduser().open("rb")
		try:
			yield fh
		finally:
			fh.close()
		return

	if hasattr(source, "read"):
		yield source  # type: ignore[misc]
		return

	raise TypeError("Unsupported pcap source type; expected path or binary file-like object.")


def _read_pcap_global_header(fh: BinaryIO) -> str:
	header = fh.read(24)
	if len(header) != 24:
		raise PcapDecodeError("Incomplete pcap global header.")

	magic = int.from_bytes(header[:4], "big")
	if magic not in _PCAP_MAGIC_TO_STRUCT_ENDIANNESS:
		magic_le = int.from_bytes(header[:4], "little")
		if magic_le in _PCAP_MAGIC_TO_STRUCT_ENDIANNESS:
			magic = magic_le
		else:
			raise PcapDecodeError("Unsupported pcap magic number.")

	endianness = _PCAP_MAGIC_TO_STRUCT_ENDIANNESS[magic]
	return endianness


def _iter_udp_payloads(fh: BinaryIO, endianness: str) -> Iterator[bytes]:
	packet_header_struct = struct.Struct(f"{endianness}IIII")

	while True:
		header = fh.read(packet_header_struct.size)
		if not header:
			return
		if len(header) != packet_header_struct.size:
			raise PcapDecodeError("Truncated packet header.")

		_, _, incl_len, _ = packet_header_struct.unpack(header)
		data = fh.read(incl_len)
		if len(data) != incl_len:
			raise PcapDecodeError("Truncated packet data.")

		if len(data) < _ETHERNET_HEADER_LENGTH:
			continue

		eth_type = struct.unpack_from("!H", data, 12)[0]
		payload_offset = _ETHERNET_HEADER_LENGTH
		while eth_type in _VLAN_ETHERTYPES:
			if len(data) < payload_offset + 4:
				break
			eth_type = struct.unpack_from("!H", data, payload_offset + 2)[0]
			payload_offset += 4

		if eth_type != _ETHERTYPE_IPV4:
			continue

		ip_offset = payload_offset
		if len(data) < ip_offset + _IP_HEADER_MIN_LENGTH:
			continue

		version_ihl = data[ip_offset]
		ihl = (version_ihl & 0x0F) * 4
		if ihl < _IP_HEADER_MIN_LENGTH:
			continue

		if len(data) < ip_offset + ihl:
			continue

		protocol = data[ip_offset + 9]
		if protocol != _IP_PROTOCOL_UDP:
			continue

		udp_offset = ip_offset + ihl
		if len(data) < udp_offset + _UDP_HEADER_LENGTH:
			continue

		udp_length = struct.unpack_from("!H", data, udp_offset + 4)[0]
		udp_payload_offset = udp_offset + _UDP_HEADER_LENGTH
		udp_payload_end = udp_payload_offset + max(udp_length - _UDP_HEADER_LENGTH, 0)
		if udp_payload_end > len(data):
			continue

		yield bytes(data[udp_payload_offset:udp_payload_end])


def _iter_mold_messages(payload: bytes) -> Iterator[bytes]:
	if len(payload) < 20:
		return

	msg_count = int.from_bytes(payload[18:20], "big")
	offset = 20

	for _ in range(msg_count):
		if offset + 2 > len(payload):
			break

		msg_len = int.from_bytes(payload[offset : offset + 2], "big")
		offset += 2
		end = offset + msg_len
		if end > len(payload):
			break

		yield payload[offset:end]
		offset = end


def load_itch_bytes_from_pcap(source: str | Path | BinaryIO) -> bytes:
	"""Return the ITCH byte stream extracted from a pcap source."""

	return b"".join(iter_itch_messages_from_pcap(source))
