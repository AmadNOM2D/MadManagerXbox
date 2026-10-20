import zlib, struct, os
w = h = 200
raw = b""
for y in range(h):
    raw += b"\x00"  # filter byte
    for x in range(w):
        # dark blue gradient-ish, always-slightly-different nothing; solid ok for dev
        r = 27 + (x % 3)
        g = 31 + (y % 3)
        b = 39 + ((x + y) % 3)
        raw += bytes([r, g, b, 255])
def chunk(t, d):
    c = t + d
    return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
sig = b"\x89PNG\r\n\x1a\n"
ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)  # 8-bit RGBA
idat = zlib.compress(raw, 9)
png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
out = "/Users/mw/xbox-agent/uwp/Assets/StoreLogo.png"
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "wb").write(png)
print("wrote", out, len(png), "bytes")
