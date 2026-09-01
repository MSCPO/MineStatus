"""Unit tests for MineStatus status querying logic."""

from unittest import mock

import pytest

from api import MineStatus


@pytest.mark.parametrize("server_type", ["java", "bedrock"])
async def test_get_server_stats_success(server_type, monkeypatch, real_java_response, real_bedrock_response):
    """A successful query returns a formatted status dict and caches the result."""
    response = real_java_response if server_type == "java" else real_bedrock_response

    async def fake_get(key):
        return None

    async def fake_handle(host):
        return response

    monkeypatch.setattr(MineStatus.server_cache, "get", fake_get)
    monkeypatch.setattr(MineStatus.server_cache, "set", mock.AsyncMock())
    handler = "handle_java_stats" if server_type == "java" else "handle_bedrock_stats"
    monkeypatch.setattr(MineStatus, handler, fake_handle)

    parsed = await MineStatus.get_server_stats(
        "example.com", server_type, use_cache=True
    )

    assert parsed["online"] is True
    assert parsed["players"] == {"online": response.players.online, "max": response.players.max}
    MineStatus.server_cache.set.assert_awaited_once()


async def test_get_server_stats_unsupported_type():
    """An unsupported server type returns an error dict."""
    parsed = await MineStatus.get_server_stats("example.com", "unknown", use_cache=False)
    assert "error" in parsed
    assert "Unsupported server type" in parsed["error"]


async def test_get_server_stats_java_success(monkeypatch, mock_java_server, real_java_response):
    """Pure Java server query returns valid status."""
    monkeypatch.setattr(
        MineStatus.JavaServer, "async_lookup", mock.AsyncMock(return_value=mock_java_server)
    )

    parsed = await MineStatus.get_server_stats("java.example.com", "java", use_cache=False)
    assert parsed["online"] is True
    assert parsed["players"] == {"online": 100, "max": 500}
    assert parsed["icon"] == real_java_response.icon
    assert "error" not in parsed


async def test_get_server_stats_bedrock_success(monkeypatch, mock_bedrock_server):
    """Pure Bedrock server query returns valid status."""
    monkeypatch.setattr(
        MineStatus.BedrockServer, "lookup", mock.Mock(return_value=mock_bedrock_server)
    )

    parsed = await MineStatus.get_server_stats("bedrock.example.com", "bedrock", use_cache=False)
    assert parsed["online"] is True
    assert parsed["players"] == {"online": 50, "max": 100}
    assert parsed["icon"] is None
    assert "error" not in parsed


async def test_get_server_stats_java_failure(monkeypatch):
    """A Java connection failure returns an error dict, not an exception."""

    async def fail(*args, **kwargs):
        raise TimeoutError("connection timed out")

    monkeypatch.setattr(MineStatus.JavaServer, "async_lookup", fail)
    parsed = await MineStatus.get_server_stats("unreachable.com", "java", use_cache=False)
    assert "error" in parsed
    assert "unreachable.com" in parsed["error"]


async def test_unclassified_java_only(monkeypatch):
    """Auto-detection returns Java result when only Java is reachable."""

    async def fake_get(host, server_type, use_cache=False):
        if server_type == "java":
            return {
                "online": True,
                "players": {"online": 100, "max": 500},
                "delay": 42.5,
                "version": "1.20.4",
                "motd": {"plain": "Java Server", "html": "", "minecraft": "", "ansi": ""},
                "icon": None,
            }
        return {"error": "offline"}

    monkeypatch.setattr(MineStatus, "get_server_stats", fake_get)
    result = await MineStatus.unclassified("server.com", use_cache=False)
    assert result["online"] is True
    assert "error" not in result


async def test_unclassified_bedrock_only(monkeypatch):
    """Auto-detection returns Bedrock result when only Bedrock is reachable."""

    async def fake_get(host, server_type, use_cache=False):
        if server_type == "bedrock":
            return {
                "online": True,
                "players": {"online": 50, "max": 100},
                "delay": 120.0,
                "version": "1.20.81",
                "motd": {"plain": "Bedrock Server", "html": "", "minecraft": "", "ansi": ""},
                "icon": None,
            }
        return {"error": "offline"}

    monkeypatch.setattr(MineStatus, "get_server_stats", fake_get)
    result = await MineStatus.unclassified("server.com", use_cache=False)
    assert result["online"] is True
    assert "error" not in result


async def test_unclassified_none_offline(monkeypatch):
    """Auto-detection returns an error when both types are unreachable."""

    async def fake_get(host, server_type, use_cache=False):
        return {"error": "offline"}

    monkeypatch.setattr(MineStatus, "get_server_stats", fake_get)
    result = await MineStatus.unclassified("server.com", use_cache=False)
    assert "error" in result


def test_format_motd(real_java_response):
    """format_motd returns the four expected encodings."""
    motd = MineStatus.format_motd(real_java_response.motd)
    assert motd["plain"] == "A Minecraft Server"
    assert motd["html"] == "<p>A Minecraft Server</p>"
    assert motd["minecraft"] == "A Minecraft Server"
    assert motd["ansi"] is not None


def test_format_response_java(real_java_response):
    """format_response on a Java response includes an icon."""
    result = MineStatus.format_response(real_java_response)
    assert result["online"] is True
    assert result["players"] == {"online": 100, "max": 500}
    assert result["icon"] == "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="


def test_format_response_bedrock(real_bedrock_response):
    """format_response on a Bedrock response has icon None."""
    result = MineStatus.format_response(real_bedrock_response)
    assert result["online"] is True
    assert result["icon"] is None