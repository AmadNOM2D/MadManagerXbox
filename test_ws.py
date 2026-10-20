import asyncio, json, os, base64, struct

HOST = "127.0.0.1"
PORT = 8765
PATH = "/ws"


def _mask(data: bytes) -> bytes:
    key = os.urandom(4)
    out = bytes(b ^ k for b, k in zip(data, (key * (len(data) // 4 + 1))))
    frame = bytearray()
    frame.append(0x81)  # FIN + text opcode
    n = len(data)
    if n < 126:
        frame.append(0x80 | n)
        frame += key
    elif n < 65536:
        frame.append(0x80 | 126)
        frame += struct.pack(">H", n)
        frame += key
    else:
        frame.append(0x80 | 127)
        frame += struct.pack(">Q", n)
        frame += key
    return bytes(frame) + out


async def read_frame(reader):
    b1 = await reader.readexactly(1)
    b2 = await reader.readexactly(1)
    opcode = b1[0] & 0x0F
    masked = b2[0] & 0x80
    length = b2[0] & 0x7F
    if length == 126:
        length = struct.unpack(">H", await reader.readexactly(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", await reader.readexactly(8))[0]
    mask_key = await reader.readexactly(4) if masked else b""
    payload = await reader.readexactly(length) if length else b""
    if masked:
        payload = bytes(b ^ m for b, m in zip(payload, (mask_key * (len(payload) // 4 + 1))))
    return opcode, payload


async def ws_connect():
    reader, writer = await asyncio.open_connection(HOST, PORT)
    key = base64.b64encode(os.urandom(16)).decode()
    handshake = (
        f"GET {PATH} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    )
    writer.write(handshake.encode())
    await writer.drain()
    while True:
        line = await reader.readline()
        if line == b"\r\n":
            break
    return reader, writer


async def main():
    reader, writer = await ws_connect()
    print("connected")

    def send_text(text):
        writer.write(_mask(text.encode()))
        return writer.drain()

    async def recv():
        return await read_frame(reader)

    prompt = "What is the current date and hostname? Use the bash tool."
    await send_text(json.dumps({"type": "chat", "content": prompt}))
    print("sent:", prompt)
    deadline = asyncio.get_event_loop().time() + 90
    try:
        while asyncio.get_event_loop().time() < deadline:
            opcode, payload = await asyncio.wait_for(recv(), timeout=60)
            if opcode == 0x8:  # close frame
                print("  (server closed connection)")
                break
            data = payload.decode(errors="replace")
            try:
                d = json.loads(data)
            except json.JSONDecodeError:
                print("  raw:", data[:120])
                continue
            t = d.get("type")
            if t == "delta":
                print("  delta:", repr(d.get("content", "")[:80]))
            elif t == "tool":
                print("  TOOL:", d.get("name"), "=>", d.get("arg"))
            elif t == "tool_result":
                print("  RESULT:", repr(d.get("content", "")[:160]))
            elif t == "tool_done":
                print("  (tool done)")
            elif t == "end":
                print("  END")
                break
            else:
                print("  event:", t)
    except asyncio.TimeoutError:
        print("  (timed out)")
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass
    print("done")


asyncio.run(main())
