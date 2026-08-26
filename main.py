"""MineStatus - a lightweight Minecraft server status query API."""

import uvicorn
from typing import Annotated, Optional, Union

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api import MineStatus

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MineStatus API",
    description="A lightweight Minecraft server status query API.",
    version="0.2.0",
    contact={"name": "MSCPO", "url": "https://github.com/MSCPO/MineStatus"},
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # Allow all origins
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class MotdInfo(BaseModel):
    """Server MOTD in multiple encodings."""

    plain: str
    html: str
    minecraft: str
    ansi: str


class PlayersInfo(BaseModel):
    """Player count information."""

    online: int
    max: int


class StatusResponse(BaseModel):
    """Status result for an online server."""

    online: bool
    players: PlayersInfo
    delay: float
    version: str
    motd: MotdInfo
    icon: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error message (e.g. server unreachable)."""

    error: str


ApiResponse = Union[StatusResponse, ErrorResponse]

# ---------------------------------------------------------------------------
# Shared parameters
# ---------------------------------------------------------------------------

IpParam = Annotated[
    str,
    Query(description="Minecraft server address/IP to query, e.g. play.example.com"),
]

CacheParam = Annotated[
    bool,
    Query(
        description=(
            "Whether to use the cached result. Defaults to true; "
            "set false to force a fresh query."
        ),
    ),
]

TAG = "Minecraft Status"

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get(
    "/",
    response_model=ApiResponse,
    summary="Query server status (auto-detect Java / Bedrock)",
    description=(
        "Tries Java and Bedrock in parallel and returns the first successful "
        "status result; returns an error if both fail."
    ),
    tags=[TAG],
)
async def status_unclassified(ip: IpParam, cache: CacheParam = True):
    """Auto-detect and query the server status."""
    return await MineStatus.unclassified(ip, cache)


@app.get(
    "/java/",
    response_model=ApiResponse,
    summary="Query Java Edition server status",
    description=(
        "Queries a Java server over the Java status protocol and returns "
        "player counts, version, MOTD and the server icon."
    ),
    tags=[TAG],
)
async def status_java(ip: IpParam, cache: CacheParam = True):
    """Query a Java Edition server status."""
    return await MineStatus.get_server_stats(ip, "java", cache)


@app.get(
    "/bedrock/",
    response_model=ApiResponse,
    summary="Query Bedrock Edition server status",
    description=(
        "Queries a Bedrock server over the Bedrock status protocol and "
        "returns player counts, version and MOTD."
    ),
    tags=[TAG],
)
async def status_bedrock(ip: IpParam, cache: CacheParam = True):
    """Query a Bedrock Edition server status."""
    return await MineStatus.get_server_stats(ip, "bedrock", cache)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
