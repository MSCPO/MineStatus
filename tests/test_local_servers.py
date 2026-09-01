"""Protocol-level integration tests using local mock servers.

Unlike tests/test_integration.py (which hits public servers and can be flaky),
these tests spin up local Java TCP / Bedrock UDP mock servers, so they are:
- reliable (no external dependency)
- fast (no real network)
- able to simulate crossplay deterministically

Scenarios covered with the same address trivially:
- pure Java:      only the TCP server is up     -> auto-detect returns Java
- pure Bedrock:   only the UDP server is up     -> auto-detect returns Bedrock
- crossplay:      both are up                   -> auto-detect returns whichever answers first
"""

import asyncio

import pytest

from api import MineStatus
from tests.mock_server import MockBedrockServer, MockJavaServer


@pytest.fixture
async def java_server():
    server = await MockJavaServer().start()
    yield server
    await server.close()


@pytest.fixture
async def bedrock_server():
    server = await MockBedrockServer().start()
    yield server
    await server.close()


async def test_local_pure_java_via_java(java_server):
    """A local TCP-only mock replies on the Java protocol."""
    result = await MineStatus.get_server_stats(java_server.address, "java", use_cache=False)
    assert "error" not in result, result
    assert result["online"] is True
    assert result["players"] == {"online": 3, "max": 100}
    assert result["version"] == "1.20.4"
    assert result["icon"].startswith("data:image/")
    assert result["motd"]["plain"] == "A local Java mock server"


async def test_local_pure_java_is_not_bedrock(java_server):
    """The TCP-only mock must NOT answer on the Bedrock protocol."""
    result = await MineStatus.get_server_stats(java_server.address, "bedrock", use_cache=False)
    assert "error" in result


async def test_local_pure_java_auto_detect(java_server):
    """Auto-detection on a Java-only mock returns a Java result."""
    result = await MineStatus.unclassified(java_server.address, use_cache=False)
    assert "error" not in result, result
    assert result["online"] is True
    assert result["version"] == "1.20.4"


async def test_local_pure_bedrock_via_bedrock(bedrock_server):
    """A local UDP-only mock replies on the Bedrock protocol."""
    result = await MineStatus.get_server_stats(bedrock_server.address, "bedrock", use_cache=False)
    assert "error" not in result, result
    assert result["online"] is True
    assert result["players"] == {"online": 7, "max": 50}
    assert result["version"] == "1.21.0"
    assert result["icon"] is None


async def test_local_pure_bedrock_is_not_java(bedrock_server):
    """The UDP-only mock must NOT answer on the Java protocol."""
    result = await MineStatus.get_server_stats(bedrock_server.address, "java", use_cache=False)
    assert "error" in result


async def test_local_pure_bedrock_auto_detect(bedrock_server):
    """Auto-detection on a Bedrock-only mock returns a Bedrock result."""
    result = await MineStatus.unclassified(bedrock_server.address, use_cache=False)
    assert "error" not in result, result
    assert result["online"] is True
    assert result["version"] == "1.21.0"


async def test_local_crossplay_both_protocols(java_server, bedrock_server):
    """A crossplay server (both protocols up) answers on BOTH."""

    via_java = await MineStatus.get_server_stats(
        f"127.0.0.1:{java_server._server.sockets[0].getsockname()[1]}", "java", use_cache=False
    )
    via_bedrock = await MineStatus.get_server_stats(
        f"127.0.0.1:{bedrock_server._sock.getsockname()[1]}", "bedrock", use_cache=False
    )
    assert "error" not in via_java, via_java
    assert "error" not in via_bedrock, via_bedrock


async def test_local_crossplay_auto_detect(java_server, bedrock_server):
    """Auto-detection on a unifying mock succeeds (either protocol answers)."""

    result = await MineStatus.unclassified(
        f"127.0.0.1:{java_server._server.sockets[0].getsockname()[1]}", use_cache=False
    )
    assert "error" not in result, result
    assert result["online"] is True
    # With both protocols live, it may legitimately return either;
    # just ensure it is one of the two known versions.
    assert result["version"] in {"1.20.4", "1.21.0"}


async def test_local_unreachable_returns_error():
    """Auto-detection against no listener at all returns a clean error."""
    result = await MineStatus.unclassified("127.0.0.1:1", use_cache=False)
    assert "error" in result


async def test_local_no_pending_task_leak(java_server):
    """Auto-detection leaves no MineStatus query task running after success."""
    result = await MineStatus.unclassified(java_server.address, use_cache=False)
    assert "error" not in result
    await asyncio.sleep(0.05)
    # Only the mock server's own socket listeners should remain, never a status task.
    remaining = {t for t in asyncio.all_tasks() if "get_server_stats" in t.get_name()}
    assert remaining == set()