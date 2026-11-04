import struct



CRC_TABLE = []
for _i in range(256):
    _r = _i << 24
    for _ in range(8):
        _r = ((_r << 1) ^ 0x04c11db7) & 0xFFFFFFFF if _r & 0x80000000 else (_r << 1) & 0xFFFFFFFF
    CRC_TABLE.append(_r)



def ogg_crc(data: bytes) -> int:
    c = 0
    for b in data:
        c = ((c << 8) & 0xFFFFFFFF) ^ CRC_TABLE[((c >> 24) & 0xFF) ^ b]
    return c



def ogg_page(pkt: bytes, granule: int, seq: int, htype: int = 0) -> bytes:
    segs, rem = [], len(pkt)
    while rem >= 255:
        segs.append(255); rem -= 255
    segs.append(rem)
    hdr = struct.pack('<4sBBqIIIB', b'OggS', 0, htype, granule, 0x12345678, seq, 0, len(segs)) + bytes(segs)
    p = hdr + pkt
    return p[:22] + struct.pack('<I', ogg_crc(p)) + p[26:]



def build_ogg_opus(pkts: list[bytes], rate: int = 48000, ch: int = 1) -> bytes:
    out, seq = b'', 0
    head = b'OpusHead' + bytes([1, ch]) + struct.pack('<HIhB', 312, rate, 0, 0)
    out += ogg_page(head, 0, seq, 0x02); seq += 1
    v = b'DeepSeek'
    tags = b'OpusTags' + struct.pack('<I', len(v)) + v + struct.pack('<I', 0)
    out += ogg_page(tags, 0, seq); seq += 1
    g, n = 0, len(pkts)
    for i, p in enumerate(pkts):
        g += 960
        out += ogg_page(p, g, seq, 0x04 if i == n - 1 else 0)
        seq = (seq + 1) & 0xFFFFFFFF
    return out