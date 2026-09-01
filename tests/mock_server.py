"""Local mock Java (TCP) and Bedrock (UDP) Minecraft servers for tests.

These speak just enough of the Minecraft status protocols for mcstatus to
successfully query them, so tests do not depend on third-party public servers.

- Java:   TCP socket, Minecraft 1.7+ status protocol (handshake + status request).
- Bedrock: UDP socket, RakNet Unconnected Ping/Pong.

Start both for a crossplay (unifying/Geyser-style) mock server; start only one
to simulate a pure-Java or pure-Bedrock server.
"""

import asyncio
import json
import random
import socket
import struct
from contextlib import AsyncExitStack
from dataclasses import dataclass


def encode_varint(value: int) -> bytes:
    """Encode an integer as a Minecraft-style varint (7-bit groups)."""
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


async def read_varint(reader: asyncio.StreamReader) -> int:
    """Read a varint from a stream reader."""
    result = 0
    for shift in range(0, 35, 7):
        byte = (await reader.readexactly(1))[0]
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result
    raise ValueError("varint too long")


def java_status_json(motd: str, version: str, online: int, max: int) -> bytes:
    """Build a Java status response JSON payload."""
    payload = {
        "version": {"name": version, "protocol": 765},
        "players": {"max": max, "online": online, "sample": []},
        "description": {"text": motd},
        "favicon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
    }
    return json.dumps(payload).encode("utf-8")


@dataclass(eq=False)
class MockJavaServer:
    """Tiny asyncio TCP server implementing the Minecraft status protocol."""

    motd: str = "A local Java mock server"
    version: str = "1.20.4"
    online: int = 3
    max: int = 100
    port: int = 0  # 0 => OS-assigned free port
    latency_ms: tuple[float, float] = (0.0, 0.0)  # random latency range (min, max)
    offline_rate: float = 0.0  # probability (0..1) of refusing connection

    _server: asyncio.Server | None = None
    _stack: AsyncExitStack | None = None

    @property
    def address(self) -> str:
        """Address string usable as a minecraft host (with port)."""
        assert self._server is not None, "not started"
        port = self._server.sockets[0].getsockname()[1]
        return f"127.0.0.1:{port}"

    async def start(self) -> "MockJavaServer":
        """Start serving until close() is called."""
        self._stack = AsyncExitStack()

        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            peer = writer.get_extra_info("peername")
            print(f"  [mock-java] ACCEPT connection from {peer}", flush=True)
            try:
                # simulate a server that is temporarily offline
                if self.offline_rate > 0 and random.random() < self.offline_rate:
                    print(f"  [mock-java] OFFLINE for {peer}", flush=True)
                    writer.close()
                    return
                delay = random.uniform(*self.latency_ms)
                if delay > 0:
                    await asyncio.sleep(delay)
                # 1. handshake packet: varint(len) + [varint(0) + varint(proto) + utf(host) + ushort(port) + varint(1)]
                length = await read_varint(reader)
                await reader.readexactly(length)
                print(f"  [mock-java] handshake read from {peer}", flush=True)
                # 2. status request: varint(len) + [varint(0)]
                length = await read_varint(reader)
                await reader.readexactly(length)
                # 3. respond with status packet
                json_bytes = java_status_json(self.motd, self.version, self.online, self.max)
                body = encode_varint(0) + encode_varint(len(json_bytes)) + json_bytes
                writer.write(encode_varint(len(body)) + body)
                await writer.drain()
                print(f"  [mock-java] RESPONDED to {peer}", flush=True)
            except Exception as exc:
                print(f"  [mock-java] ERROR {type(exc).__name__}: {exc}", flush=True)
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except (ConnectionResetError, OSError):
                    pass

        self._server = await asyncio.start_server(handle, "127.0.0.1", self.port)
        return self

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None


def _build_bedrock_pong(time_bytes: bytes) -> bytes:
    """Build a RakNet Unconnected Pong reply for an Unconnected Ping."""

    magic = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")
    server_guid = b"\x00\x01\x02\x03\x04\x05\x06\x07"
    name = (
        "MCPE;A local Bedrock mock server;630;1.21.0;7;50;"
        "LOCAL0000000000001;world;Survival;1;19132;19133;"
    ).encode("utf-8")
    return (
        b"\x1c"
        + time_bytes
        + server_guid
        + magic
        + struct.pack(">H", len(name))
        + name
    )


@dataclass(eq=False)
class MockBedrockServer:
    """Tiny UDP (RakNet) server answering Unconnected Ping with a Pong."""

    port: int = 0  # 0 => OS-assigned free port
    latency_ms: tuple[float, float] = (0.0, 0.0)  # random latency range
    offline_rate: float = 0.0  # probability (0..1) of not replying

    _sock: socket.socket | None = None
    _task: asyncio.Task | None = None

    @property
    def address(self) -> str:
        """Address string usable as a bedrock host (with port)."""
        assert self._sock is not None, "not started"
        port = self._sock.getsockname()[1]
        return f"127.0.0.1:{port}"

    async def start(self) -> "MockBedrockServer":
        """Start the UDP listener until close() is called."""
        loop = asyncio.get_running_loop()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)
        self._sock.bind(("127.0.0.1", self.port))

        async def serve() -> None:
            assert self._sock is not None
            while True:
                try:
                    data, addr = await loop.sock_recvfrom(self._sock, 2048)
                except OSError:
                    return
                if data and data[0] == 0x01 and len(data) >= 9:  # Unconnected Ping
                    # simulate latency and offline behaviour per query
                    if self.offline_rate > 0 and random.random() < self.offline_rate:
                        continue
                    delay = random.uniform(*self.latency_ms)
                    if delay > 0:
                        await asyncio.sleep(delay)
                    pong = _build_bedrock_pong(data[1:9])
                    try:
                        await loop.sock_sendto(self._sock, pong, addr)
                    except OSError:
                        return

        self._task = asyncio.create_task(serve())
        return self

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None


class MockUnifyingServers:
    """Start a Java TCP + Bedrock UDP listener = a crossplay (unifying) server."""

    def __init__(self) -> None:
        self.java = MockJavaServer()
        self.bedrock = MockBedrockServer()
        self._started = False

    async def start(self) -> "MockUnifyingServers":
        await self.java.start()
        await self.bedrock.start()
        self._started = True
        return self

    async def close(self) -> None:
        if self._started:
            await asyncio.gather(
                self.java.close(),
                self.bedrock.close(),
                return_exceptions=True,
            )
            self._started = False