"""MineStatus - a lightweight Minecraft server status query API."""

import base64
from importlib.metadata import version
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api import MineStatus

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MineStatus API",
    description="A lightweight Minecraft server status query API.",
    version=version("minestatus"),
    contact={"name": "MSCPO", "url": "https://github.com/MSCPO/MineStatus"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
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
    icon: str | None = None


class ErrorResponse(BaseModel):
    """Error message (e.g. server unreachable)."""

    error: str


ApiResponse = StatusResponse | ErrorResponse

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


_JAVA_ICON_SUFFIX = "/icon"


async def get_java_icon(host: str, use_cache: bool = True) -> Response:
    """Query the Java server and return its icon as a PNG image.

    Raises HTTPException(404) when the server is unreachable or has no icon.
    """
    result = await MineStatus.get_server_stats(host, "java", use_cache)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    icon: str = result.get("icon") or ""
    if not icon.startswith("data:image/") or "," not in icon:
        raise HTTPException(status_code=404, detail="Server has no icon")
    try:
        data = base64.b64decode(icon.split(",", 1)[1])
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Invalid icon data") from exc
    return Response(content=data, media_type="image/png")


@app.get(
    "/java/",
    response_model=ApiResponse,
    summary="Query Java Edition server status",
    description=(
        "Queries a Java server over the Java status protocol and returns "
        "player counts, version, MOTD and the server icon.\n\n"
        f"Append `{_JAVA_ICON_SUFFIX}` to the `ip` value to get the server "
        "icon as a PNG image instead of JSON, e.g. "
        f"`/java/?ip=example.com{_JAVA_ICON_SUFFIX}` "
        "(404 if the server is unreachable or has no icon)."
    ),
    tags=[TAG],
    responses={
        200: {
            "content": {"application/json": {}, "image/png": {}},
            "description": "Server status JSON, or the icon PNG when ip ends with /icon",
        },
        404: {
            "model": ErrorResponse,
            "description": "Server unreachable or no icon available",
        },
    },
)
async def status_java(ip: IpParam, cache: CacheParam = True):
    """Query a Java Edition server status (append /icon to ip for the icon PNG)."""
    if ip.endswith(_JAVA_ICON_SUFFIX):
        return await get_java_icon(ip[: -len(_JAVA_ICON_SUFFIX)], cache)
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
