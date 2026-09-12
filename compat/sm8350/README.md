# OnePlus 9 / 9 Pro stock network message layouts

The pinned public OnePlus source has an older network protobuf schema than the
final registered ColorOS boot image. The original Image exports
register_netlink_request with CRC 0x8ed24291; the unmodified public schema produces
0xabc386f7. Changing the export CRC alone would hide a real type-layout mismatch.

protocol-reflection.json records the 27 message descriptors and two enums
recovered from the original Image, including field tags, types, labels, offsets,
quantifier offsets, flags and structure sizes. Its stock_boot_sha256 identifies
the registered OnePlus 9 / 9 Pro ColorOS image.

netlink_msg.proto reconstructs those declarations. The oneof names follow the
existing public schema; ordinary declaration order follows the recorded memory
offsets. scripts/prepare_protocol.py generates protobuf-c sources and appends
compile-time size and offset checks against every recorded field. The build
manifest records both input hashes.

This restores message declarations and serialization support. It does not
reconstruct private DPI algorithms or handlers absent from the public source.
Matching export CRCs is a separate check and does not establish runtime or CFI
compatibility. No CRC is overwritten to force a match.
