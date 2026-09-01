"""Shared fixtures for MineStatus tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from mcstatus.motd import Motd
from mcstatus.responses import (
    BedrockStatusPlayers,
    BedrockStatusResponse,
    BedrockStatusVersion,
    JavaStatusPlayers,
    JavaStatusResponse,
    JavaStatusVersion,
)

JAVA_VERSION = "1.20.4"
BEDROCK_VERSION = "1.20.81"


@pytest.fixture
def real_java_response():
    """Create a real JavaStatusResponse object."""
    return JavaStatusResponse(
        players=JavaStatusPlayers(online=100, max=500, sample=None),
        version=JavaStatusVersion(name=JAVA_VERSION, protocol=765),
        motd=Motd.parse("A Minecraft Server"),
        latency=42.5,
        raw={},
        enforces_secure_chat=True,
        icon="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
        forge_data=None,
    )


@pytest.fixture
def real_bedrock_response():
    """Create a real BedrockStatusResponse object."""
    return BedrockStatusResponse(
        players=BedrockStatusPlayers(online=50, max=100),
        version=BedrockStatusVersion(name=BEDROCK_VERSION, protocol=671, brand="BDS"),
        motd=Motd.parse("Bedrock Server"),
        latency=120.0,
        map_name="world",
        gamemode="Survival",
    )


@pytest.fixture
def mock_java_server(real_java_response):
    """Create a mock JavaServer returning the real Java response."""
    server = MagicMock()
    server.async_status = AsyncMock(return_value=real_java_response)
    return server


@pytest.fixture
def mock_bedrock_server(real_bedrock_response):
    """Create a mock BedrockServer returning the real Bedrock response."""
    server = MagicMock()
    server.async_status = AsyncMock(return_value=real_bedrock_response)
    return server