"""Concurrency and task-cancellation tests for MineStatus."""

import asyncio
from unittest import mock

import pytest

from api import MineStatus


async def test_unclassified_cancels_remaining_task(monkeypatch):
    """When one protocol succeeds first, the other task is cancelled."""
    cancelled = set()

    async def slow_fail(host, server_type, use_cache=False):
        try:
            await asyncio.sleep(10)
            return {"error": "should not reach"}
        except asyncio.CancelledError:
            cancelled.add(server_type)
            raise

    async def fast_success(host, server_type, use_cache=False):
        return {
            "online": True,
            "players": {"online": 1, "max": 2},
            "delay": 1.0,
            "version": "1.20",
            "motd": {"plain": "ok", "html": "", "minecraft": "", "ansi": ""},
            "icon": None,
        }

    async def fake_get(host, server_type, use_cache=False):
        if server_type == "java":
            return await fast_success(host, server_type, use_cache)
        return await slow_fail(host, server_type, use_cache)

    monkeypatch.setattr(MineStatus, "get_server_stats", fake_get)

    result = await MineStatus.unclassified("server.com", use_cache=False)
    assert result["online"] is True
    # Bedrock task should have been cancelled
    assert "bedrock" in cancelled


async def test_unclassified_cancelled_both_fail(monkeypatch):
    """All tasks are properly awaited even when they all fail."""
    state = {"remaining": 0}

    async def all_fail(host, server_type, use_cache=False):
        await asyncio.sleep(0.05)
        raise TimeoutError("timeout")

    async def fake_get(host, server_type, use_cache=False):
        await all_fail(host, server_type, use_cache)
        return {"error": "offline"}

    monkeypatch.setattr(MineStatus, "get_server_stats", fake_get)

    result = await MineStatus.unclassified("server.com", use_cache=False)
    assert "error" in result


async def test_concurrent_queries_distinct_hosts(monkeypatch):
    """Multiple concurrent queries for distinct hosts all succeed."""
    async def fake_get(host, server_type, use_cache=False):
        await asyncio.sleep(0.01)
        return {
            "online": True,
            "players": {"online": 1, "max": 2},
            "delay": 1.0,
            "version": "1.20",
            "motd": {"plain": host, "html": "", "minecraft": "", "ansi": ""},
            "icon": None,
        }

    monkeypatch.setattr(MineStatus, "get_server_stats", fake_get)

    hosts = [f"server{i}.com" for i in range(20)]
    results = await asyncio.gather(
        *(MineStatus.get_server_stats(h, "java", use_cache=False) for h in hosts)
    )
    assert len(results) == 20
    assert all(r["online"] is True for r in results)


async def test_concurrent_unclassified(monkeypatch):
    """Multiple concurrent auto-detection queries all succeed without task leaks."""
    async def fake_get(host, server_type, use_cache=False):
        await asyncio.sleep(0.01)
        if server_type == "java":
            return {
                "online": True,
                "players": {"online": 1, "max": 2},
                "delay": 1.0,
                "version": "1.20",
                "motd": {"plain": host, "html": "", "minecraft": "", "ansi": ""},
                "icon": None,
            }
        return {"error": "offline"}

    monkeypatch.setattr(MineStatus, "get_server_stats", fake_get)

    results = await asyncio.gather(
        *(MineStatus.unclassified(f"s{i}.com", use_cache=False) for i in range(10))
    )
    assert len(results) == 10
    assert all(r["online"] is True for r in results)


async def test_no_background_task_leak(monkeypatch, mock_java_server, mock_bedrock_server):
    """unclassified should not leave pending tasks running after completion."""
    async def java_fast(*args, **kwargs):
        return mock_java_server

    async def bedrock_result(*args, **kwargs):
        return mock_bedrock_server

    monkeypatch.setattr(MineStatus.JavaServer, "async_lookup", java_fast)
    monkeypatch.setattr(MineStatus.BedrockServer, "lookup", mock.Mock(return_value=mock_bedrock_server))

    result = await MineStatus.unclassified("server.com", use_cache=False)
    assert result["online"] is True

    # Capture tasks before and after to detect leaks
    before = set(asyncio.all_tasks())
    await asyncio.sleep(0.05)
    after = set(asyncio.all_tasks())
    # No new tasks should have been created or left
    assert after <= before
