import asyncio
from mcstatus import BedrockServer, JavaServer
from mcstatus.status_response import BedrockStatusResponse, JavaStatusResponse
from mcstatus.motd import Motd
from .ServerCache import ServerCache


server_cache = ServerCache(ttl=600)  # 10 minutes

async def get_server_stats(host: str, server_type: str):
    """
    Retrieves the status of a Minecraft server (either Java or Bedrock).

    Args:
        host (str): The hostname or IP address of the server to query.
        server_type (str): The type of the server, either 'java' or 'bedrock'.

    Returns:
        dict: A dictionary containing the server's status or an error message.
    """
    try:
        cache_key = f"{host}_{server_type}"  # 用host和server_type作为缓存的键
        cached_result = await server_cache.get(cache_key)
        if cached_result:
            return cached_result

        if server_type == "java":
            response = await handle_java_stats(host)
        elif server_type == "bedrock":
            response = await handle_bedrock_stats(host)
        else:
            raise ValueError("Unsupported server type")

        result = format_response(response)
        await server_cache.set(cache_key, result)
        return result

    except Exception as e:
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
        server = await JavaServer.async_lookup(host)
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
        server = BedrockServer.lookup(host)
        return await server.async_status()
    except Exception as e:
        raise ValueError(f"Failed to connect to Bedrock server at {host}: {e}") from e


async def unclassified(host: str):
    """
    Retrieves the status of a Minecraft server, which can be either Java or Bedrock.

    Args:
        host (str): The hostname or IP address of the server to query.

    Returns:
        dict: A dictionary containing the server's status or an error message.
    """
    server_types = ["java", "bedrock"]
    tasks = [
        asyncio.create_task(get_server_stats(host, server_type))
        for server_type in server_types
    ]

    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if "error" not in result:
                return result
        except Exception:
            continue

    return {"error": "No server status detected, Is server offline?"}


def format_response(response: JavaStatusResponse | BedrockStatusResponse) -> dict:
    """
    Formats the server status response into a dictionary with the required structure.

    Args:
        response (JavaStatusResponse | BedrockStatusResponse): The server status response.

    Returns:
        dict: A dictionary containing the formatted server status information.
    """
    if isinstance(response, (JavaStatusResponse, BedrockStatusResponse)):
        return {
            "online": True,
            "players": {
                "online": response.players.online,
                "max": response.players.max,
            },
            "delay": response.latency,
            "version": response.version.name,
            "motd": format_motd(response.motd),
        }
    else:
        raise ValueError("Unexpected response type")


def format_motd(motd: Motd) -> dict:
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
