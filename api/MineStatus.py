import asyncio
import logging
from typing import TypedDict, cast

from mcstatus import BedrockServer, JavaServer
from mcstatus.motd import Motd
from mcstatus.responses import BedrockStatusResponse, JavaStatusResponse

from .ServerCache import ServerCache

server_cache = ServerCache(ttl=600)  # 10 minutes

# DNS + connection budget per status query (seconds). Keep this generous:
# some resolvers need more than 3s for DNS alone.
TIMEOUT = 8

logger = logging.getLogger(__name__)


class MotdDict(TypedDict):
    """MOTD in multiple encodings."""

    plain: str
    html: str
    minecraft: str
    ansi: str


class PlayersDict(TypedDict):
    """Player counts."""

    online: int
    max: int


class StatusDict(TypedDict):
    """Status result of an online server."""

    online: bool
    players: PlayersDict
    delay: float
    version: str
    motd: MotdDict
    icon: str | None


class ErrorDict(TypedDict):
    """Error result."""

    error: str


QueryResult = StatusDict | ErrorDict


async def get_server_stats(
    host: str, server_type: str, use_cache: bool = True
) -> QueryResult:
    """
    Retrieves the status of a Minecraft server (either Java or Bedrock).

    Args:
        host (str): The hostname or IP address of the server to query.
        server_type (str): The type of the server, either 'java' or 'bedrock'.
        use_cache (bool): Whether to read/write the cache. Defaults to True.

    Returns:
        QueryResult: The server's status or an error message.
    """
    try:
        cache_key = f"{host}_{server_type}"  # Cache key based on host and server type
        if use_cache:
            cached_result = cast(
                QueryResult | None, await server_cache.get(cache_key)
            )
            if cached_result:
                return cached_result
        response: JavaStatusResponse | BedrockStatusResponse | None = None
        if server_type == "java":
            response = await handle_java_stats(host)
        elif server_type == "bedrock":
            response = await handle_bedrock_stats(host)
        else:
            raise ValueError("Unsupported server type")

        result = format_response(response)
        if use_cache:
            await server_cache.set(cache_key, result)
        return result

    except (ValueError, OSError) as e:
        return {"error": str(e)}


async def handle_java_stats(host: str) -> JavaStatusResponse:
    """
    Pings a Java Minecraft server and returns its status.

    Args:
        host (str): The hostname or IP address of the Java server to query.

    Returns:
        JavaStatusResponse: The status of the Java Minecraft server.

    Raises:
        ValueError: If the connection to the Java server fails.
    """
    try:
        server = await JavaServer.async_lookup(host, timeout=TIMEOUT)
        return await server.async_status()
    except Exception as e:
        raise ValueError(f"Failed to connect to Java server at {host}: {e}") from e


async def handle_bedrock_stats(host: str) -> BedrockStatusResponse:
    """
    Pings a Bedrock Minecraft server and returns its status.

    Args:
        host (str): The hostname or IP address of the Bedrock server to query.

    Returns:
        BedrockStatusResponse: The status of the Bedrock Minecraft server.

    Raises:
        ValueError: If the connection to the Bedrock server fails.
    """
    try:
        server = BedrockServer.lookup(host, timeout=TIMEOUT)
        return await server.async_status()
    except Exception as e:
        raise ValueError(f"Failed to connect to Bedrock server at {host}: {e}") from e


async def unclassified(host: str, use_cache: bool = True) -> QueryResult:
    """
    Retrieves the status of a Minecraft server, which can be either Java or Bedrock.

    Args:
        host (str): The hostname or IP address of the server to query.
        use_cache (bool): Whether to read/write the cache. Defaults to True.

    Returns:
        QueryResult: The server's status or an error message.
    """
    server_types = ["java", "bedrock"]
    tasks = [
        asyncio.create_task(get_server_stats(host, server_type, use_cache))
        for server_type in server_types
    ]

    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if "error" not in result:
                return result
        except (ValueError, OSError) as exc:
            logger.warning("Status query failed for %s: %s", host, exc)
            continue

    return {"error": "No server status detected, Is server offline?"}


def format_response(
    response: JavaStatusResponse | BedrockStatusResponse,
) -> StatusDict:
    """
    Formats the server status response into a dictionary with the required structure.

    Args:
        response (JavaStatusResponse | BedrockStatusResponse): The server status response.

    Returns:
        StatusDict: A dictionary containing the formatted server status information.
    """
    if isinstance(response, JavaStatusResponse):
        return {
            "online": True,
            "players": {
                "online": response.players.online,
                "max": response.players.max,
            },
            "delay": response.latency,
            "version": response.version.name,
            "motd": format_motd(response.motd),
            "icon": response.icon,
        }
    return {
        "online": True,
        "players": {
            "online": response.players.online,
            "max": response.players.max,
        },
        "delay": response.latency,
        "version": response.version.name,
        "motd": format_motd(response.motd),
        "icon": None,
    }


def format_motd(motd: Motd) -> MotdDict:
    """
    Helper function to format the Message of the Day (MOTD) into various formats.

    Args:
        motd: The MOTD object that contains the server's message.

    Returns:
        dict: A dictionary with the MOTD in different formats such as plain, HTML, Minecraft, and ANSI.
    """
    return {
        "plain": motd.to_plain(),
        "html": motd.to_html(),
        "minecraft": motd.to_minecraft(),
        "ansi": motd.to_ansi(),
    }
