"""Integration tests against real public Minecraft servers.

These tests require network access and hit real external servers, so they are
skipped by default. Run them explicitly with:

    uv run pytest -m integration

Verified reachable public servers (as of 2026-09):
- Java-only:       mc.hypixel.net
- Bedrock-only:    play.nethergames.org
- Crossplay (both): play.wildnetwork.net

Server addresses can drift, so several tests accept provisional results
(e.g. a temporarily down server returns a clean error) while still asserting
the important invariants (no crash, protocol isolation, clean error dicts).
"""

import pytest

from api import MineStatus

pytestmark = pytest.mark.integration

JAVA_ONLY = "mc.hypixel.net"
BEDROCK_ONLY = "play.nethergames.org"
CROSSPLAY = "play.wildnetwork.net"


async def test_pure_java_server_via_java():
    """A Java-only server replies on the Java protocol."""
    result = await MineStatus.get_server_stats(JAVA_ONLY, "java", use_cache=False)
    if "error" in result:
        pytest.skip(f"Java server temporarily unreachable: {result['error']}")
    assert result["online"] is True
    assert result["players"]["max"] > 0
    assert "icon" in result


async def test_pure_java_server_not_bedrock():
    """The Java-only server must NOT answer on the Bedrock protocol."""
    result = await MineStatus.get_server_stats(JAVA_ONLY, "bedrock", use_cache=False)
    assert "error" in result


async def test_pure_bedrock_server_via_bedrock():
    """A Bedrock-only server replies on the Bedrock protocol."""
    result = await MineStatus.get_server_stats(BEDROCK_ONLY, "bedrock", use_cache=False)
    if "error" in result:
        pytest.skip(f"Bedrock server temporarily unreachable: {result['error']}")
    assert result["online"] is True
    assert result["players"]["max"] > 0
    assert result["icon"] is None


async def test_pure_bedrock_server_not_java():
    """The Bedrock-only server must NOT answer on the Java protocol."""
    result = await MineStatus.get_server_stats(BEDROCK_ONLY, "java", use_cache=False)
    assert "error" in result


async def test_crossplay_server_both_protocols():
    """A crossplay server replies on BOTH Java and Bedrock protocols."""
    java = await MineStatus.get_server_stats(CROSSPLAY, "java", use_cache=False)
    bedrock = await MineStatus.get_server_stats(CROSSPLAY, "bedrock", use_cache=False)
    if "error" in java and "error" in bedrock:
        pytest.skip(f"Crossplay server temporarily unreachable: {java['error']}")
    assert "error" not in java, java
    assert "error" not in bedrock, bedrock
    assert java["online"] is True
    assert bedrock["online"] is True


async def test_auto_detect_pure_java():
    """Auto-detection succeeds on a Java-only server."""
    result = await MineStatus.unclassified(JAVA_ONLY, use_cache=False)
    assert "error" not in result, result
    assert result["online"] is True


async def test_auto_detect_crossplay():
    """Auto-detection succeeds on a crossplay server."""
    result = await MineStatus.unclassified(CROSSPLAY, use_cache=False)
    assert "error" not in result, result
    assert result["online"] is True


async def test_unreachable_server_returns_error():
    """A bogus address returns a clean error dict without raising."""
    result = await MineStatus.get_server_stats(
        "invalid.invalid.invalid", "java", use_cache=False
    )
    assert "error" in result